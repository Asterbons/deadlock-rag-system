"""
Shop Extractor Pipeline — Orchestrates KV3 parsing, localization merging,
item extraction, and shop.json generation.
"""

import json
import sys
import logging
from pathlib import Path

# Add src/ and heroes_abilities_extractor to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "heroes_abilities_extractor"))

from kv3_parser import parse_kv3_file
from hero_extractor import extract_shop_data
from shop_builder import parse_localization, extract_items, build_shop_json

from config import RAW_DATA_DIR, SHOP_JSON_PATH

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main():
    print("Loading abilities.vdata...")
    abilities_dict = parse_kv3_file(RAW_DATA_DIR / "abilities.vdata")

    print("Loading heroes.vdata (for purchase bonuses)...")
    heroes_dict = parse_kv3_file(RAW_DATA_DIR / "heroes.vdata")

    print("Extracting purchase bonuses...")
    shop_data = extract_shop_data(heroes_dict)
    purchase_bonuses = shop_data.get("purchase_bonuses", {})

    print("Parsing localization...")
    localization = parse_localization(
        RAW_DATA_DIR / "citadel_mods_english.txt",
        RAW_DATA_DIR / "citadel_gc_mod_names_english.txt"
    )
    print(f"  Display names: {len(localization['display_names'])}")
    print(f"  Descriptions: {len(localization['descriptions'])}")

    print("Extracting items...")
    items = extract_items(abilities_dict, localization)
    print(f"  Items extracted: {len(items)}")

    # Count by slot
    by_slot = {}
    for item in items:
        slot = item.get("slot", "unknown")
        by_slot[slot] = by_slot.get(slot, 0) + 1
    for slot, count in sorted(by_slot.items()):
        print(f"    {slot}: {count}")

    # Count items with proc effects
    with_proc = sum(1 for i in items if "proc" in i)
    with_upgrade = sum(1 for i in items if "upgrade" in i)
    print(f"  Items with proc: {with_proc}")
    print(f"  Items with upgrade: {with_upgrade}")

    print("Building shop.json...")
    shop_json = build_shop_json(items, purchase_bonuses)

    print(f"Saving {SHOP_JSON_PATH}...")
    with SHOP_JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump(shop_json, f, indent=2, ensure_ascii=False)

    file_size_kb = SHOP_JSON_PATH.stat().st_size / 1024
    print(f"Done! shop.json is {file_size_kb:.1f} KB")


if __name__ == "__main__":
    main()
