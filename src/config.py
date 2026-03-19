from pathlib import Path

# Base Directories
SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"

RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# Raw Data Files
HEROES_VDATA_PATH = RAW_DATA_DIR / "heroes.vdata"
ABILITIES_VDATA_PATH = RAW_DATA_DIR / "abilities.vdata"

# Raw Localization Files
HERO_NAMES_LOC_PATH = RAW_DATA_DIR / "citadel_gc_hero_names_english.txt"
HEROES_LOC_PATH = RAW_DATA_DIR / "citadel_heroes_english.txt"
ATTRIBUTES_LOC_PATH = RAW_DATA_DIR / "citadel_attributes_english.txt"
MODS_LOC_PATH = RAW_DATA_DIR / "citadel_mods_english.txt"

# Processed Data Files
PROCESSED_HEROES_PATH = PROCESSED_DATA_DIR / "processed_heroes.json"
SHOP_JSON_PATH = PROCESSED_DATA_DIR / "shop.json"
REPORT_TXT_PATH = PROCESSED_DATA_DIR / "report.txt"
HEROES_OUT_DIR = PROCESSED_DATA_DIR / "heroes"
HEROES_INDEX_PATH = PROCESSED_DATA_DIR / "heroes_index.json"
CHUNKS_JSON_PATH = PROCESSED_DATA_DIR / "chunks.json"
