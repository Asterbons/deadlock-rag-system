import json
import logging
from pathlib import Path
import sys

# Adjust paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from kv3_parser import parse_kv3_file
from config import (
    SHOP_JSON_PATH, HEROES_VDATA_PATH, ABILITIES_VDATA_PATH,
    HERO_NAMES_LOC_PATH, HEROES_LOC_PATH, ATTRIBUTES_LOC_PATH, MODS_LOC_PATH,
    HEROES_OUT_DIR, HEROES_INDEX_PATH
)

from localization import parse_localization
from profile_builder import extract_hero_profile, create_index_entry

logger = logging.getLogger(__name__)

def load_shop_valid_items():
    valid = {}
    try:
        with open(SHOP_JSON_PATH, "r", encoding="utf-8") as f:
            shop = json.load(f)
            for category in ["weapon", "vitality", "spirit"]:
                for item in shop.get(category, []):
                    valid[item["id"]] = item.get("name", item["id"])
    except Exception as e:
        print(f"Error loading shop.json: {e}")
    return valid

def main():
    print("Loading VDATA files...")
    heroes_data = parse_kv3_file(HEROES_VDATA_PATH)
    abilities_data = parse_kv3_file(ABILITIES_VDATA_PATH)
    
    print("Parsing localization...")
    loc = parse_localization(
        HERO_NAMES_LOC_PATH,
        HEROES_LOC_PATH,
        ATTRIBUTES_LOC_PATH,
        MODS_LOC_PATH
    )

    base_stats_fallback = heroes_data.get("hero_base", {}).get("m_mapStartingStats", {})
    base_scaling_fallback = heroes_data.get("hero_base", {}).get("m_mapStandardLevelUpUpgrades", {})

    HEROES_OUT_DIR.mkdir(parents=True, exist_ok=True)
    index_data = []

    print("Loading valid shop items...")
    valid_items = load_shop_valid_items()

    print("Extracting heroes...")
    for key, data in heroes_data.items():
        if not key.startswith("hero_") or key == "hero_base":
            continue
        if not isinstance(data, dict):
            continue
            
        def is_true(v):
            if isinstance(v, str): return v.lower() == "true"
            return bool(v)
            
        # Filter unreleased/test heroes
        if not is_true(data.get("m_bPlayerSelectable", False)): continue
        if is_true(data.get("m_bDisabled", False)): continue
        if is_true(data.get("m_bInDevelopment", False)): continue
        if is_true(data.get("m_bNeedsTesting", False)): continue
        if is_true(data.get("m_bLimitedTesting", False)): continue
        if is_true(data.get("m_bPrereleaseOnly", False)): continue

        hero = extract_hero_profile(key, data, base_stats_fallback, base_scaling_fallback, loc, abilities_data, valid_items)
        
        # Save detailed 
        hero_filename = hero["name"].lower().replace(" & ", "_and_").replace(" ", "_").replace("'", "")
        with open(HEROES_OUT_DIR / f"{hero_filename}.json", "w", encoding="utf-8") as f:
            json.dump(hero, f, indent=2, ensure_ascii=False)
            
        # Put in index
        index_data.append(create_index_entry(hero))

    # Save index
    with open(HEROES_INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)
        
    print(f"Extraction complete! Saved {len(index_data)} heroes to data/processed/heroes/ and data/processed/heroes_index.json")

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    main()
