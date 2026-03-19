"""
Main Pipeline — Orchestrates hero profile extraction and file generation.

Steps:
  1. Run hero_profile_extractor to generate heroes/ and heroes_index.json
  2. Combine all individual hero JSONs into processed_heroes.json
  3. Generate report.txt
"""

import json
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import HEROES_OUT_DIR, HEROES_INDEX_PATH, PROCESSED_HEROES_PATH, REPORT_TXT_PATH

import hero_profile_extractor


def main():
    # Step 1: Run hero_profile_extractor to generate heroes/ and heroes_index.json

    print("Step 1: Running hero_profile_extractor...")
    hero_profile_extractor.main()

    # Step 2: Combine all individual hero JSONs into processed_heroes.json
    print()
    print("Step 2: Combining hero files into processed_heroes.json...")

    all_heroes = {}
    hero_files = sorted(HEROES_OUT_DIR.glob("*.json"))
    for hero_file in hero_files:
        with open(hero_file, "r", encoding="utf-8") as f:
            hero_data = json.load(f)
        hero_key = hero_data.get("hero", hero_file.stem)
        all_heroes[hero_key] = hero_data

    with PROCESSED_HEROES_PATH.open("w", encoding="utf-8") as f:
        json.dump(all_heroes, f, indent=2, ensure_ascii=False)

    print(f"  Combined {len(all_heroes)} heroes into processed_heroes.json")

    # Step 3: Generate report.txt
    print()
    print("Step 3: Generating report.txt...")

    total_abilities = sum(
        len(h.get("abilities", [])) for h in all_heroes.values()
    )
    file_size_kb = PROCESSED_HEROES_PATH.stat().st_size / 1024
    avg_size_kb = file_size_kb / len(all_heroes) if all_heroes else 0

    report_text = (
        f"Обработано {len(all_heroes)} героев\n"
        f"Найдено {total_abilities} способностей\n"
        f"Средний размер профиля героя — {avg_size_kb:.2f}кб\n"
    )

    REPORT_TXT_PATH.write_text(report_text, encoding="utf-8")

    print("Pipeline complete!")
    print(report_text)


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    main()
