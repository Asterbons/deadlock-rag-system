"""Exploration script for deadlock-api.com (corrected to real schema).

Real endpoints discovered via /openapi.json (68 paths total).

Steps:
  1. Probe a representative slice of real endpoints.
  2. Find latest balance patch via /v1/patches/big-days, cross-ref /v1/patches.
  3. Download 500-match sample via /v1/matches/metadata with all include_* on.
  4. List SQL tables via /v1/sql/tables (replaces nonexistent S3 dump bucket).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = "https://api.deadlock-api.com"
HEADERS = {"User-Agent": "DeadlockOracle/1.0 (educational project)"}

PROJECT_ROOT = Path(__file__).resolve().parents[1]
META_DIR = PROJECT_ROOT / "data" / "meta"
META_DIR.mkdir(parents=True, exist_ok=True)


def _preview(obj, limit: int = 400) -> str:
    return json.dumps(obj, indent=2, default=str)[:limit]


def _describe_keys(d: dict, indent: str = "    ") -> None:
    for k, v in d.items():
        vt = type(v).__name__
        extra = ""
        if isinstance(v, (str, int, float, bool)) or v is None:
            sval = str(v)
            extra = f" = {sval[:60]}"
        elif isinstance(v, list):
            extra = f" (list len={len(v)})"
            if v and isinstance(v[0], dict):
                extra += f" item_keys={list(v[0].keys())[:8]}"
        elif isinstance(v, dict):
            extra = f" (dict keys={list(v.keys())[:8]})"
        print(f"{indent}{k} :: {vt}{extra}")


def probe_endpoints() -> dict:
    endpoints = [
        "/v1/info",
        "/v1/info/health",
        "/v1/patches",
        "/v1/patches/big-days",
        "/v1/matches/active",
        "/v1/matches/recently-fetched",
        "/v1/sql/tables",
        "/v1/analytics/hero-stats?min_average_badge=80",
    ]
    results: dict = {}
    print("=" * 60)
    print("STEP 1 - Endpoint probes (real paths from openapi.json)")
    print("=" * 60)
    for ep in endpoints:
        url = BASE + ep
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
        except requests.RequestException as e:
            print(f"GET {ep} -> ERROR {e}\n")
            results[ep] = {"status": None, "error": str(e)}
            continue
        print(f"GET {ep} -> {resp.status_code}")
        info: dict = {"status": resp.status_code}
        if resp.ok:
            try:
                data = resp.json()
            except ValueError:
                print(f"  Non-JSON body: {resp.text[:200]}\n")
                info["body_preview"] = resp.text[:200]
                results[ep] = info
                continue
            if isinstance(data, list):
                info["type"] = "array"
                info["length"] = len(data)
                if data:
                    info["item_type"] = type(data[0]).__name__
                    if isinstance(data[0], dict):
                        info["item_keys"] = list(data[0].keys())
                    print(f"  Array [{len(data)}] item0={_preview(data[0], 200)}")
            elif isinstance(data, dict):
                info["type"] = "dict"
                info["keys"] = list(data.keys())
                print(f"  Dict keys: {info['keys']}")
                print(f"  Sample: {_preview(data, 200)}")
        else:
            print(f"  Body: {resp.text[:200]}")
            info["body_preview"] = resp.text[:200]
        print()
        results[ep] = info
    return results


def find_latest_balance_patch() -> dict | None:
    print("=" * 60)
    print("STEP 2 - Latest balance patch (/v1/patches/big-days + /v1/patches)")
    print("=" * 60)

    big_days_url = BASE + "/v1/patches/big-days"
    big_resp = requests.get(big_days_url, headers=HEADERS, timeout=30)
    print(f"GET /v1/patches/big-days -> {big_resp.status_code}")
    big_days: list[str] = []
    if big_resp.ok:
        try:
            payload = big_resp.json()
            if isinstance(payload, list):
                big_days = [str(x) for x in payload]
            elif isinstance(payload, dict):
                for k in ("dates", "big_days", "data"):
                    if isinstance(payload.get(k), list):
                        big_days = [str(x) for x in payload[k]]
                        break
        except ValueError:
            print(f"  non-JSON: {big_resp.text[:200]}")
    print(f"  Big days returned: {len(big_days)}")
    if big_days:
        print("  Last 5:", big_days[-5:])

    patches_resp = requests.get(BASE + "/v1/patches", headers=HEADERS, timeout=30)
    if not patches_resp.ok:
        print(f"  /v1/patches failed: {patches_resp.status_code}")
        return None
    patches = patches_resp.json()
    print(f"  /v1/patches notes: {len(patches)} entries")

    def _date_of(p: dict) -> datetime | None:
        raw = p.get("pub_date") or p.get("published") or p.get("date")
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None

    patches_dated = sorted(
        ((p, _date_of(p)) for p in patches if _date_of(p)),
        key=lambda x: x[1],
        reverse=True,
    )

    latest_balance = None
    if big_days:
        big_set = {d.split("T")[0] for d in big_days}
        for p, dt in patches_dated:
            if dt.date().isoformat() in big_set:
                latest_balance = (p, dt)
                break

    if not latest_balance:
        print("  No big-day match in /v1/patches; defaulting to most recent note.")
        latest_balance = patches_dated[0] if patches_dated else None

    if not latest_balance:
        return None

    p, dt = latest_balance
    record = {
        "patch_id": p.get("guid", {}).get("text") if isinstance(p.get("guid"), dict) else p.get("guid"),
        "patch_date": dt.date().isoformat(),
        "patch_datetime": dt.isoformat(),
        "patch_unix": int(dt.timestamp()),
        "patch_name": p.get("title"),
        "link": p.get("link"),
        "is_big_day": bool(big_days and dt.date().isoformat() in {d.split("T")[0] for d in big_days}),
    }
    out = META_DIR / "latest_patch.json"
    out.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"\n  Latest balance patch:")
    print(f"    {record['patch_name']} | {record['patch_date']} | unix={record['patch_unix']}")
    print(f"    is_big_day={record['is_big_day']}")
    print(f"  Saved -> {out.relative_to(PROJECT_ROOT)}")
    return record


def download_match_sample(patch: dict | None) -> dict | None:
    print("=" * 60)
    print("STEP 3 - Match sample via /v1/matches/metadata")
    print("=" * 60)
    params: dict = {
        "limit": 500,
        "include_info": "true",
        "include_player_info": "true",
        "include_player_items": "true",
        "include_player_stats": "true",
        "include_objectives": "true",
        "min_average_badge": 80,
        "game_mode": "normal",
        "order_by": "match_id",
        "order_direction": "desc",
    }
    if patch and patch.get("patch_unix"):
        params["min_unix_timestamp"] = patch["patch_unix"]

    url = BASE + "/v1/matches/metadata"
    print(f"GET {url}")
    print(f"  params: {params}")
    resp = requests.get(url, headers=HEADERS, params=params, timeout=180)
    print(f"  -> {resp.status_code}")
    if not resp.ok:
        print(f"  body: {resp.text[:500]}")
        return None

    body = resp.json()
    matches = body if isinstance(body, list) else body.get("matches") or body.get("data") or []
    print(f"  matches downloaded: {len(matches)}")
    out = META_DIR / "matches_sample.json"
    out.write_text(json.dumps(body, indent=2, default=str), encoding="utf-8")
    print(f"  Saved -> {out.relative_to(PROJECT_ROOT)}  ({out.stat().st_size/1024:.1f} KB)")

    if matches:
        sample = matches[0]
        print("\n  --- match top-level keys ---")
        if isinstance(sample, dict):
            _describe_keys(sample)
            match_info = sample.get("match_info") if isinstance(sample.get("match_info"), dict) else None
            container = match_info or sample
            players = None
            for k in ("players", "match_players", "playerstats", "team_players"):
                if isinstance(container.get(k), list):
                    players = container[k]
                    break
            if players:
                print(f"\n  --- player[0] keys (n_players={len(players)}) ---")
                _describe_keys(players[0])
                items_field = None
                for k in ("items", "purchased_items", "abilities", "stats"):
                    if isinstance(players[0].get(k), list):
                        items_field = (k, players[0][k])
                        break
                if items_field:
                    print(f"\n  --- player[0].{items_field[0]}[0] (sample item shape) ---")
                    if items_field[1] and isinstance(items_field[1][0], dict):
                        _describe_keys(items_field[1][0])

    return {"params": params, "count": len(matches)}


def list_sql_tables() -> dict:
    print("=" * 60)
    print("STEP 4 - SQL tables (replaces S3 dump bucket which doesn't exist)")
    print("=" * 60)
    url = BASE + "/v1/sql/tables"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    print(f"GET /v1/sql/tables -> {resp.status_code}")
    out: dict = {"status": resp.status_code}
    if resp.ok:
        try:
            tables = resp.json()
            print(f"  tables ({len(tables) if isinstance(tables, list) else '?'}):")
            print(f"  {json.dumps(tables, indent=2)[:1500]}")
            out["tables"] = tables
            (META_DIR / "sql_tables.json").write_text(
                json.dumps(tables, indent=2), encoding="utf-8"
            )
        except ValueError:
            print(f"  non-JSON: {resp.text[:300]}")
    else:
        print(f"  body: {resp.text[:300]}")
    return out


def main() -> None:
    endpoint_results = probe_endpoints()
    patch_record = find_latest_balance_patch()
    sample_info = download_match_sample(patch_record)
    sql_info = list_sql_tables()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("Working endpoints:")
    for ep, info in endpoint_results.items():
        print(f"  {info.get('status')}  {ep}")
    if patch_record:
        print(
            f"\nLatest balance patch: {patch_record['patch_name']} "
            f"({patch_record['patch_date']}, big_day={patch_record['is_big_day']})"
        )
    if sample_info:
        print(f"\nMatch sample: count={sample_info['count']}")
    print(f"\nSQL tables: {len(sql_info.get('tables') or [])}")


if __name__ == "__main__":
    main()
