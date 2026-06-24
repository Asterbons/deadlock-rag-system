import json
import logging

from psycopg2.extras import execute_values
from tqdm import tqdm

from src.meta.db import ensure_patch, get_conn
from src.meta.migrate import run_migrations

logger = logging.getLogger(__name__)

LATEST_PATCH_DATE = "2026-05-02"
LATEST_PATCH_NAME = "02-05-2026 Update"


def load_matches_batch(
    matches: list, conn, patch_date: str = LATEST_PATCH_DATE
) -> tuple[int, int]:
    """Insert a batch of match objects into PostgreSQL.

    Caller owns the connection: this function does NOT run migrations,
    commit, or close. Returns (loaded, skipped) where loaded counts
    inserted matches (excluding ON CONFLICT collisions on the DB side
    which still count as "loaded" from the API's perspective) and
    skipped counts client-side rejections (not_scored / empty / no
    winning team).
    """
    match_rows: list = []
    player_rows: list = []
    item_rows: list = []
    skipped = 0

    for m in matches:
        if m.get("not_scored"):
            skipped += 1
            continue
        if not m.get("players"):
            skipped += 1
            continue

        winning_team = m.get("winning_team") or ""
        if not winning_team:
            skipped += 1
            continue

        match_mode = m.get("match_mode", "Normal")

        match_rows.append((
            m["match_id"],
            m.get("start_time"),
            m.get("duration_s"),
            match_mode,
            m.get("match_outcome"),
            winning_team,
            m.get("average_badge_team0", 0),
            m.get("average_badge_team1", 0),
            patch_date,
        ))

        for p in m.get("players", []):
            won = p.get("team") == winning_team
            player_rows.append((
                m["match_id"],
                p.get("player_slot"),
                p.get("hero_id"),
                p.get("team"),
                won,
                p.get("kills", 0),
                p.get("deaths", 0),
                p.get("assists", 0),
                p.get("net_worth", 0),
                p.get("player_level", 0),
                match_mode,
                patch_date,
            ))

            for item in p.get("items", []):
                if not item.get("item_id"):
                    continue
                item_rows.append((
                    m["match_id"],
                    p.get("hero_id"),
                    item["item_id"],
                    item.get("game_time_s", 0),
                    (item.get("sold_time_s") or 0) > 0,
                    won,
                    match_mode,
                    patch_date,
                ))

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO matches
              (match_id, start_time, duration_s, match_mode,
               match_outcome, winning_team,
               badge_team0, badge_team1, patch_date)
            VALUES %s
            ON CONFLICT (match_id) DO NOTHING
            """,
            match_rows,
            page_size=1000,
        )

        execute_values(
            cur,
            """
            INSERT INTO players
              (match_id, player_slot, hero_id, team, won,
               kills, deaths, assists, net_worth,
               player_level, match_mode, patch_date)
            VALUES %s
            ON CONFLICT (match_id, player_slot) DO NOTHING
            """,
            player_rows,
            page_size=1000,
        )

        execute_values(
            cur,
            """
            INSERT INTO item_purchases
              (match_id, hero_id, item_id, game_time_s,
               sold, won, match_mode, patch_date)
            VALUES %s
            ON CONFLICT (match_id, hero_id, item_id, game_time_s)
              DO NOTHING
            """,
            item_rows,
            page_size=1000,
        )

    logger.debug(
        "batch: %d matches, %d players, %d items (skipped %d)",
        len(match_rows),
        len(player_rows),
        len(item_rows),
        skipped,
    )
    return len(match_rows), skipped


def load_matches_from_file(filepath: str):
    run_migrations()

    with open(filepath, encoding="utf-8") as f:
        matches = json.load(f)

    conn = get_conn()
    try:
        ensure_patch(conn, LATEST_PATCH_DATE, LATEST_PATCH_NAME, is_balance=True)
        loaded, skipped = load_matches_batch(
            tqdm(matches, desc="Processing matches"), conn, LATEST_PATCH_DATE
        )
        conn.commit()
        logger.info("Loaded: %d matches (skipped %d)", loaded, skipped)
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    load_matches_from_file("data/meta/matches_sample.json")
