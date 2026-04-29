from pathlib import Path
import os
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
WIKI_DATA_PATH = PROCESSED_DATA_DIR / "wiki_data.json"

# Updater
UPDATE_INTERVAL_HOURS = 6  # how often the scheduler checks for game updates (supports decimals, e.g. 0.5 = 30 min)

# Wiki
WIKI_BASE_URL = "https://deadlock.wiki"
WIKI_API_URL = f"{WIKI_BASE_URL}/api.php"

# Qdrant
QDRANT_URL = "http://localhost:6333"
VECTOR_SIZE = 1024

# Indexing
BATCH_SIZE = 50

# Embeddings
EMBEDDING_TRUNCATE_CHARS = 1000  # Ollama embeddings endpoint errors on very long inputs.

# Retrieval
DEFAULT_TOP_K = 3
FULL_INDEX_TOP_K = 38  # top_k for whole-roster ranking queries (one chunk per hero)

# RAG generation
HISTORY_WINDOW = 6     # number of recent (user/assistant) messages kept in prompt context
TOOL_LOOP_MAX = 5      # max iterations of LLM ↔ tool-call loop before giving up

# Collections
COLLECTIONS = {
    "hero":    "deadlock_heroes",
    "ability": "deadlock_abilities",
    "item":    "deadlock_items",
    "lore":    "deadlock_lore",
    "guide":   "deadlock_guides",
}

# Provider selection: "ollama" | "openai" | "azure"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")

# Ollama
OLLAMA_URL   = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-r1:7b-qwen-distill-q4_K_M")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Azure OpenAI
AZURE_OPENAI_API_KEY    = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_ENDPOINT   = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")

# Embeddings 
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "mxbai-embed-large")