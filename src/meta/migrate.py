import logging
from pathlib import Path

from src.meta.db import get_conn

logger = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def run_migrations():
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        logger.info("schema applied from %s", SCHEMA_PATH.name)
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run_migrations()
    print("schema applied")
