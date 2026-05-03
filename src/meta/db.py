import psycopg2

from src.config import POSTGRES_DSN


def get_conn():
    return psycopg2.connect(POSTGRES_DSN)


def ensure_patch(conn, patch_date, patch_name=None, is_balance=False):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO patches (patch_date, patch_name, is_balance_patch)
            VALUES (%s, %s, %s)
            ON CONFLICT (patch_date) DO NOTHING
            """,
            (patch_date, patch_name, is_balance),
        )
    conn.commit()
