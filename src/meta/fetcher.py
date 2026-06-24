"""Download all high-badge matches since the latest balance patch
into PostgreSQL via src.meta.loader.load_matches_batch."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import requests
from tqdm import tqdm

from src.meta.db import ensure_patch, get_conn
from src.meta.loader import load_matches_batch
from src.meta.migrate import run_migrations

logger = logging.getLogger(__name__)

BASE = "https://api.deadlock-api.com"
HEADERS = {"User-Agent": "DeadlockOracle/1.0 (educational project)"}

BATCH_SIZE = 500
SLEEP_BETWEEN_BATCHES = 1
MIN_BADGE = 80
MAX_RETRIES = 6

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LATEST_PATCH_FILE = PROJECT_ROOT / "data" / "meta" / "latest_patch.json"


def _load_patch_info() -> dict:
    with open(LATEST_PATCH_FILE, encoding="utf-8") as f:
        return json.load(f)


def _resume_max_match_id(conn, patch_date: str) -> int | None:
    """Return MIN(match_id) - 1 for already-loaded matches on this patch
    so we continue walking older matches without re-fetching them."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT MIN(match_id) FROM matches WHERE patch_date = %s",
            (patch_date,),
        )
        row = cur.fetchone()
    if row and row[0] is not None:
        return int(row[0]) - 1
    return None


def _fetch_batch(params: dict) -> list:
    """GET one page with retry/backoff on 429 + 5xx + connection errors.
    Returns the parsed list of match dicts (possibly empty)."""
    url = f"{BASE}/v1/matches/metadata"
    backoff = 5
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=180)
        except (requests.ConnectionError, requests.Timeout) as e:
            logger.warning(
                "Network error (%s) attempt %d/%d — sleeping %ds",
                type(e).__name__, attempt, MAX_RETRIES, backoff,
            )
            time.sleep(backoff)
            backoff = min(backoff * 2, 120)
            continue

        if resp.status_code == 429:
            logger.warning("429 rate limited — sleeping 60s")
            time.sleep(60)
            continue
        if 500 <= resp.status_code < 600:
            logger.warning(
                "%d server error attempt %d/%d — sleeping %ds",
                resp.status_code, attempt, MAX_RETRIES, backoff,
            )
            time.sleep(backoff)
            backoff = min(backoff * 2, 120)
            continue

        resp.raise_for_status()
        body = resp.json()
        if isinstance(body, list):
            return body
        return body.get("matches") or body.get("data") or []

    raise RuntimeError(
        f"Exhausted {MAX_RETRIES} retries for {url} params={params}"
    )


def fetch_and_load_all(max_batches: int | None = None) -> None:
    patch = _load_patch_info()
    patch_unix = patch["patch_unix"]
    patch_date = patch["patch_date"]
    patch_name = patch["patch_name"]

    run_migrations()
    conn = get_conn()
    total_loaded = 0
    total_skipped = 0
    batches_done = 0
    try:
        ensure_patch(conn, patch_date, patch_name, is_balance=True)

        max_match_id = _resume_max_match_id(conn, patch_date)
        if max_match_id is not None:
            logger.info("Resuming from max_match_id=%d", max_match_id)

        with tqdm(desc="Fetching matches", unit="match") as pbar:
            while True:
                params: dict = {
                    "limit": BATCH_SIZE,
                    "min_average_badge": MIN_BADGE,
                    "min_unix_timestamp": patch_unix,
                    "include_info": "true",
                    "include_player_info": "true",
                    "include_player_items": "true",
                    "order_by": "match_id",
                    "order_direction": "desc",
                }
                if max_match_id is not None:
                    params["max_match_id"] = max_match_id

                batch = _fetch_batch(params)

                if not batch:
                    logger.info("No more matches — done")
                    break

                loaded, skipped = load_matches_batch(batch, conn, patch_date)
                conn.commit()
                total_loaded += loaded
                total_skipped += skipped
                pbar.update(loaded)

                max_match_id = min(m["match_id"] for m in batch) - 1
                batches_done += 1

                if max_batches is not None and batches_done >= max_batches:
                    logger.info("Reached max_batches=%d, stopping", max_batches)
                    break
                if len(batch) < BATCH_SIZE:
                    logger.info("Final partial batch (%d) — done", len(batch))
                    break

                time.sleep(SLEEP_BETWEEN_BATCHES)
    finally:
        conn.close()

    logger.info(
        "Done: %d loaded, %d skipped across %d batches",
        total_loaded,
        total_skipped,
        batches_done,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    fetch_and_load_all()
