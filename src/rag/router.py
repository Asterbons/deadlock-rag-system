import json
import logging
import os

import requests

logger = logging.getLogger(__name__)

import sys
PROJ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

from src.config import OLLAMA_URL, LLM_MODEL

_INDEX_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "processed", "heroes_index.json"
)

# ── Module-load: build hero_ids string and HERO_ID_MAP ──────────────────────

hero_ids_string = ""
HERO_ID_MAP: dict[str, str] = {}
HERO_ALIASES: dict[str, str] = {}

try:
    with open(_INDEX_PATH, "r", encoding="utf-8") as f:
        _heroes = json.load(f)

    _parts = []
    for hero in _heroes:
        hero_id = hero["hero"]        # e.g. "hero_inferno"
        name    = hero.get("name", "") # e.g. "Infernus"

        _parts.append(f"{hero_id} ({name})")

        # HERO_ID_MAP: name.lower() → hero_id
        HERO_ID_MAP[name.lower()] = hero_id

        # HERO_ALIASES: for detect_hero() fallback
        HERO_ALIASES[name.lower()] = hero_id
        stripped = hero_id.replace("hero_", "")
        HERO_ALIASES[stripped] = hero_id
        for word in name.lower().split():
            if len(word) >= 4:
                HERO_ALIASES[word] = hero_id

    hero_ids_string = ", ".join(_parts)

except FileNotFoundError:
    pass  # index not yet generated

# Manual overrides
HERO_ALIASES.update({
    "seven":    "hero_gigawatt",
    "abrams":   "hero_atlas",
    "vindicta": "hero_hornet",
    "paradox":  "hero_chrono",
    "mcginnis": "hero_forge",
    "geist":    "hero_ghost",
    "mo":       "hero_krill",
    "krill":    "hero_krill",
})

# ── Prompt ───────────────────────────────────────────────────────────────────

ROUTER_PROMPT = """You are a query router for a Deadlock game RAG system.
Analyze the question and return a routing decision as JSON.

Available collections:
- "hero": hero base stats, weapon stats, scaling per level
- "ability": hero abilities, damage formulas, effects, upgrades
- "item": shop items, procs, synergies, upgrade chains

Hero IDs available (use exact spelling for hero_filter):
{hero_ids}

Rules:
- Ranking/comparison of ALL heroes (top, best, highest, lowest,
  tier list, who has most/least) → use_full_index: true
- Specific hero abilities → collections: ["ability"],
  hero_filter: hero_id
- Build/item questions for a specific hero (e.g. "good items for X",
  "what should X buy", "best build for X") → collections: ["hero", "ability", "item"],
  hero_filter: hero_id, top_k: 6
- General items/shop questions (no specific hero) → collections: ["item"]
- Full hero overview → collections: ["hero", "ability"],
  hero_filter: hero_id, top_k: 6
- General/mixed → collections: ["hero", "ability", "item"], top_k: 3

Return ONLY valid JSON:
{{
  "collections": ["hero"|"ability"|"item"],
  "use_full_index": false,
  "hero_filter": "hero_inferno" or null,
  "top_k": 3,
  "reasoning": "one line"
}}

Question: {question}"""

# ── Default route ─────────────────────────────────────────────────────────────

DEFAULT_ROUTE = {
    "collections":    ["hero", "ability", "item"],
    "use_full_index": False,
    "hero_filter":    None,
    "top_k":          3,
    "reasoning":      "default fallback",
}

# ── Public API ────────────────────────────────────────────────────────────────

def detect_hero(question: str) -> str | None:
    """Return the first hero_id whose alias appears in question, or None."""
    q = question.lower()
    for alias, hero_id in HERO_ALIASES.items():
        if alias in q:
            return hero_id
    return None


def route_query(question: str) -> dict:
    """
    Use the LLM to classify the question and return routing parameters.

    Returns a dict with keys:
        collections (list[str]), use_full_index (bool),
        hero_filter (str|None), top_k (int), reasoning (str)
    """
    import time
    try:
        prompt = ROUTER_PROMPT.format(
            hero_ids=hero_ids_string,
            question=question,
        )
        _t0 = time.time()
        print(f"[DEBUG router] calling LLM router ({LLM_MODEL})...", flush=True)
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model":   LLM_MODEL,
                "prompt":  prompt,
                "stream":  False,
                "format":  "json",
                "options": {"temperature": 0, "num_predict": 400},
                "think": False,
            },
            timeout=30,
        )
        print(f"[DEBUG router] LLM router responded in {time.time()-_t0:.2f}s", flush=True)
        raw = response.json()
        if "response" not in raw:
            print(f"[DEBUG router] unexpected Ollama response (no 'response' key): {raw}", flush=True)
        result = json.loads(raw["response"])

        # validate required fields
        assert isinstance(result.get("collections"), list)
        assert isinstance(result.get("top_k"), int)
        assert isinstance(result.get("use_full_index"), bool)

        # clamp top_k
        result["top_k"] = max(1, min(38, result["top_k"]))

        # ensure hero_filter key exists
        result.setdefault("hero_filter", None)
        result.setdefault("reasoning", "")

        logger.info(f"Route: {result['reasoning']}")
        return result

    except Exception as e:
        print(f"[DEBUG router] LLM router failed: {e}, using default", flush=True)
        logger.warning(f"LLM router failed: {e}, using default")
        return DEFAULT_ROUTE
