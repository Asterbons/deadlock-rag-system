"""Sanity-check meta tables after running src/meta/loader.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2

from src.config import POSTGRES_DSN
from src.meta.loader import LATEST_PATCH_DATE


def main():
    conn = psycopg2.connect(POSTGRES_DSN)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM matches")
    matches = cur.fetchone()[0]
    print(f"Matches: {matches}")
    assert matches > 0, "expected matches > 0"

    cur.execute("SELECT COUNT(*) FROM players")
    players = cur.fetchone()[0]
    print(f"Players: {players}")
    assert players >= matches * 10, (
        f"expected players >= 10 per match, got {players} for {matches} matches"
    )

    cur.execute("SELECT COUNT(*) FROM item_purchases")
    items = cur.fetchone()[0]
    print(f"Item purchases: {items}")
    assert items > 0, "expected item purchases > 0"

    cur.execute(
        """
        SELECT hero_id,
               COUNT(*) AS matches,
               AVG(won::int) AS win_rate
        FROM players
        WHERE patch_date = %s
        GROUP BY hero_id
        HAVING COUNT(*) >= 10
        ORDER BY win_rate DESC
        LIMIT 5
        """,
        (LATEST_PATCH_DATE,),
    )
    print()
    print("Top 5 heroes by winrate:")
    for hero_id, n, wr in cur.fetchall():
        print(f"  hero_id={hero_id}: {n} matches, {wr:.1%} winrate")

    cur.execute(
        """
        SELECT match_mode, COUNT(*)
        FROM matches
        GROUP BY match_mode
        ORDER BY COUNT(*) DESC
        """
    )
    print()
    print("Match modes:")
    for mode, n in cur.fetchall():
        print(f"  {mode}: {n} matches")

    conn.close()
    print()
    print("All checks passed")


if __name__ == "__main__":
    main()
