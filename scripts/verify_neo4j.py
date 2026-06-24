"""Sanity-check script for the Neo4j Phase 1 setup.

Verifies:
1. Neo4j connection via graph/connection.py
2. All constraints and indexes from graph_schema.py are applied
3. A simple RETURN 1 query succeeds
4. graph/counter_items.json loads and passes structural validation

Run from the project root:
    python scripts/verify_neo4j.py
"""

import json
import logging
import sys
from pathlib import Path

# Allow imports from the project root regardless of working directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from graph.connection import get_driver
from graph import graph_schema as schema

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

COUNTER_ITEMS_PATH = Path(__file__).parent.parent / "graph" / "counter_items.json"

REQUIRED_ITEM_FIELDS = {"name", "shop_category", "tier", "counters"}
VALID_CATEGORIES = {"vitality", "gun", "spirit"}
REQUIRED_COUNTER_FIELDS = {"target_type", "target_name", "weight", "weight_label", "notes"}
VALID_TARGET_TYPES = {"hero", "mechanic", "item"}
VALID_WEIGHT_LABELS = {"primary", "secondary"}


def apply_schema(driver):
    with driver.session() as session:
        for cypher in schema.CONSTRAINTS:
            session.run(cypher)
        for cypher in schema.INDEXES:
            session.run(cypher)
    logger.info(
        f"Applied {len(schema.CONSTRAINTS)} constraints, {len(schema.INDEXES)} indexes."
    )


def verify_query(driver):
    with driver.session() as session:
        result = session.run("RETURN 1 AS ping")
        assert result.single()["ping"] == 1
    logger.info("Query check passed (RETURN 1).")


def validate_counter_items():
    with open(COUNTER_ITEMS_PATH) as f:
        data = json.load(f)

    items = data.get("items")
    if not isinstance(items, list):
        raise ValueError("counter_items.json must have a top-level 'items' array.")

    errors = []
    item_names = {item.get("name") for item in items if isinstance(item, dict)}
    for idx, item in enumerate(items):
        label = item.get("name", f"item[{idx}]")

        missing = REQUIRED_ITEM_FIELDS - item.keys()
        if missing:
            errors.append(f"{label}: missing fields {missing}")
            continue

        if item["shop_category"] not in VALID_CATEGORIES:
            errors.append(
                f"{label}: invalid shop_category '{item['shop_category']}' "
                f"(expected one of {VALID_CATEGORIES})"
            )

        if not isinstance(item["tier"], int) or item["tier"] < 1:
            errors.append(f"{label}: tier must be a positive integer")

        if not isinstance(item["counters"], list):
            errors.append(f"{label}: 'counters' must be an array")
            continue

        seen_targets = set()
        for cidx, counter in enumerate(item["counters"]):
            clabel = f"{label}.counters[{cidx}]"
            missing_c = REQUIRED_COUNTER_FIELDS - counter.keys()
            if missing_c:
                errors.append(f"{clabel}: missing fields {missing_c}")
                continue
            if counter["target_type"] not in VALID_TARGET_TYPES:
                errors.append(
                    f"{clabel}: invalid target_type '{counter['target_type']}'"
                )
            if (
                counter["target_type"] == "item"
                and counter["target_name"] not in item_names
            ):
                errors.append(
                    f"{clabel}: item target '{counter['target_name']}' does not "
                    "match an item name in counter_items.json"
                )
            if counter["target_name"] in seen_targets:
                errors.append(
                    f"{clabel}: duplicate target_name '{counter['target_name']}'"
                )
            seen_targets.add(counter["target_name"])
            if counter["weight_label"] not in VALID_WEIGHT_LABELS:
                errors.append(
                    f"{clabel}: invalid weight_label '{counter['weight_label']}'"
                )
            if not isinstance(counter["weight"], (int, float)):
                errors.append(f"{clabel}: weight must be a number")

    if errors:
        for e in errors:
            logger.error(e)
        raise ValueError(f"counter_items.json validation failed with {len(errors)} error(s).")

    return len(items)


def main():
    # 1. Connect
    driver = get_driver()

    # 2. Apply schema
    apply_schema(driver)

    # 3. Smoke-test query
    verify_query(driver)

    # 4. Validate counter_items.json
    n_items = validate_counter_items()

    driver.close()

    print(
        f"\nNeo4j connected. Constraints applied. "
        f"counter_items.json valid ({n_items} items). "
        f"Ready for graph_builder.py."
    )


if __name__ == "__main__":
    main()
