import json
import logging
import os
import sys

logger = logging.getLogger(__name__)

PROJ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

from src.config import FULL_INDEX_TOP_K

_INDEX_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "processed", "heroes_index.json"
)

# ── Hero index cache (refreshed when heroes_index.json mtime changes) ───────
#
# Reading the index lazily through get_hero_aliases() / get_hero_ids_string()
# means the data stays in sync after the updater pipeline re-indexes new heroes
# without requiring a process restart.

_MANUAL_OVERRIDES = {
    "seven":    "hero_gigawatt",
    "abrams":   "hero_atlas",
    "vindicta": "hero_hornet",
    "paradox":  "hero_chrono",
    "mcginnis": "hero_forge",
    "geist":    "hero_ghost",
    "mo":       "hero_krill",
    "krill":    "hero_krill",
}

_cache_mtime: float | None = None
_cached_aliases: dict[str, str] = dict(_MANUAL_OVERRIDES)
_cached_ids_string: str = ""


def _build_from_index(heroes: list[dict]) -> tuple[dict[str, str], str]:
    aliases: dict[str, str] = {}
    parts: list[str] = []
    for hero in heroes:
        hero_id = hero["hero"]
        name = hero.get("name", "")
        parts.append(f"{hero_id} ({name})")
        aliases[name.lower()] = hero_id
        stripped = hero_id.replace("hero_", "")
        aliases[stripped] = hero_id
        for word in name.lower().split():
            if len(word) >= 4:
                aliases[word] = hero_id
    aliases.update(_MANUAL_OVERRIDES)
    return aliases, ", ".join(parts)


def _refresh_hero_index_cache() -> None:
    """Reload the alias map and ids string when heroes_index.json has changed on disk."""
    global _cache_mtime, _cached_aliases, _cached_ids_string

    try:
        mtime = os.path.getmtime(_INDEX_PATH)
    except OSError:
        # Index not yet generated — keep manual overrides only.
        return

    if _cache_mtime == mtime:
        return

    try:
        with open(_INDEX_PATH, "r", encoding="utf-8") as f:
            heroes = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Failed to read %s: %s", _INDEX_PATH, e)
        return

    _cached_aliases, _cached_ids_string = _build_from_index(heroes)
    _cache_mtime = mtime


def get_hero_aliases() -> dict[str, str]:
    _refresh_hero_index_cache()
    return _cached_aliases


def get_hero_ids_string() -> str:
    _refresh_hero_index_cache()
    return _cached_ids_string

# ── Prompt for GPT-4o-mini fallback ──────────────────────────────────────────

ROUTER_PROMPT = """You are a query router for a Deadlock game RAG system.
Analyze the question and return a routing decision as JSON.

Available collections:
- "hero": hero base stats, weapon stats, scaling per level
- "ability": hero abilities, damage formulas, effects, upgrades
- "item": shop items, procs, synergies, upgrade chains
- "lore": game world story, hero backstories, lore details
- "guide": game mechanics (laning, parrying, souls), hero playstyle strategy, hero descriptions

Hero IDs available (use exact spelling for hero_filter):
{hero_ids}

Rules:
- Ranking/comparison of ALL heroes (top, best, highest, lowest,
  tier list, who has most/least) -> use_full_index: true
- Specific hero abilities -> collections: ["ability"],
  hero_filter: hero_id
- Build/item questions for a specific hero (e.g. "good items for X",
  "what should X buy", "best build for X") -> collections: ["hero", "ability", "item"],
  hero_filter: hero_id, top_k: 6
- General items/shop questions (no specific hero) -> collections: ["item"]
- Lore/story questions (about the world, hero background) -> collections: ["lore"]
- Mechanics/how-to/strategy questions (e.g. "how to parry", "laning guide", "hero strategy") -> collections: ["guide"]
- Full hero overview -> collections: ["hero", "ability", "guide"],
  hero_filter: hero_id, top_k: 6
- General/mixed -> collections: ["hero", "ability", "item", "lore", "guide"], top_k: 3

Return ONLY valid JSON:
{{
  "collections": ["hero"|"ability"|"item"|"lore"|"guide"],
  "use_full_index": false,
  "hero_filter": "hero_inferno" or null,
  "top_k": 3,
  "reasoning": "one line"
}}

Question: {question}"""


# ── GPT-4o-mini router call ──────────────────────────────────────────────────

def _call_router_llm(question: str) -> dict:
    """Call GPT-4o-mini to classify the question and return routing params."""
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    prompt = ROUTER_PROMPT.format(
        hero_ids=get_hero_ids_string(),
        question=question,
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=400,
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)

    # ensure all keys exist
    result.setdefault("hero_filter", None)
    result.setdefault("reasoning", "GPT-4o-mini routing")
    return result


# ── Stat name → heroes_index key mapping ────────────────────────────────────

# Maps question keywords → exact key in base_stats / weapon / scaling_per_level
_STAT_NAME_MAP: dict[str, str] = {
    # health
    "base health": "health",
    "max health": "health",
    " hp ": "health",
    "most hp": "health",
    "highest hp": "health",
    "lowest hp": "health",
    "health": "health",
    # movement
    "movement speed": "max_move_speed",
    "move speed": "max_move_speed",
    "movespeed": "max_move_speed",
    "fastest hero": "max_move_speed",
    "slowest hero": "max_move_speed",
    "sprint speed": "sprint_speed",
    "crouch speed": "crouch_speed",
    "acceleration": "move_acceleration",
    "dash distance": "ground_dash_distance_in_meters",
    # melee
    "heavy melee": "heavy_melee_damage",
    "light melee": "light_melee_damage",
    "melee damage": "light_melee_damage",
    # stamina
    "stamina regen": "stamina_regen_per_second",
    "stamina": "stamina",
    # weapon
    "bullet damage": "bullet_damage",
    "bullet speed": "bullet_speed",
    "fire rate": "rounds_per_sec",
    "rounds per second": "rounds_per_sec",
    "clip size": "clip_size",
    "ammo": "clip_size",
    "reload time": "reload_time",
    "reload": "reload_time",
    # scaling
    "spirit scaling": "spirit_power",
    "spirit per level": "spirit_power",
    "spirit power": "spirit_power",
    "health scaling": "health",      # resolved against scaling_per_level
    "hp per level": "health",
    "bullet scaling": "base_bullet_damage_from_level",
    "damage scaling": "base_bullet_damage_from_level",
}


def detect_stat_name(question: str) -> str | None:
    """Return the stat key that best matches the question, or None."""
    q = question.lower()
    for kw in sorted(_STAT_NAME_MAP.keys(), key=len, reverse=True):
        if kw in q:
            return _STAT_NAME_MAP[kw]
    return None


# ── Hero detection ───────────────────────────────────────────────────────────

def detect_hero(question: str) -> str | None:
    """Return the first hero_id whose alias appears in question, or None."""
    q = question.lower()
    for alias, hero_id in get_hero_aliases().items():
        if alias in q:
            return hero_id
    return None


def detect_two_heroes(question: str) -> tuple[str, str] | None:
    """Return (hero_id_a, hero_id_b) if exactly two distinct heroes are mentioned."""
    q = question.lower()
    aliases = get_hero_aliases()
    found: list[str] = []
    # iterate longest aliases first to prefer specific names over fragments
    for alias in sorted(aliases.keys(), key=len, reverse=True):
        hero_id = aliases[alias]
        if alias in q and hero_id not in found:
            found.append(hero_id)
        if len(found) == 2:
            return found[0], found[1]
    return None


# ── Keyword routing ──────────────────────────────────────────────────────────

# Keyword sets for each category
_RANKING_KW = [
    "best", "worst", "top", "highest", "lowest",
    "most", "least", "ranking", "tier list",
    "who has", "compare all", "all heroes",
    "beginner", "easy", "hard", "complex", "difficulty",
]
_ABILITY_KW = [
    "abilit", "skill", "spell", "kit", "ult",
    "ultimate", "passive", "active", "what can",
    "moves", "powers",
]
_OVERVIEW_KW = [
    "tell me", "everything", "overview",
    "explain", "all about", "full info",
    "who is", "about",
]
_STATS_KW = [
    "health", "speed", "damage", "stats",
    "base", "scaling", "dps", "weapon",
]
_ITEM_KW = [
    "item", "buy", "shop", "build", "upgrade",
    "gold", "purchase", "recommend", "worth",
    "should i get",
]
_LORE_KW = [
    "lore", "story", "backstory", "history", "background",
    "who is", "where from", "born", "created", "origin",
    "execution", "past", "night", "happened", "lore",
]
_GUIDE_KW = [
    "guide", "how to", "strategy", "playstyle", "mechanic",
    "laning", "parry", "soul", "jungl", "creep", "boss",
    "objective", "tip", "trick", "learn", "how do i",
    "description", "overview",
]


def _has_keyword(q: str, keywords: list[str]) -> bool:
    """Check if any keyword appears in the lowered question."""
    return any(kw in q for kw in keywords)


_TWO_HERO_KW = ["vs", "versus", "compare", "difference", "better", "stronger",
                "faster", "more", "less", "who wins", "between"]


def keyword_route(question: str) -> dict:
    """
    Fast deterministic routing based on keyword matching.

    Returns a route dict with an extra "confidence" field:
        "high" — keyword match is strong, skip GPT
        "low"  — uncertain, GPT fallback recommended
    """
    q = question.lower()
    hero_id = detect_hero(question)

    # 0. TWO-HERO COMPARISON (deterministic: skip full-index, call tool directly)
    two = detect_two_heroes(question)
    if two and _has_keyword(q, _TWO_HERO_KW):
        return {
            "collections": [],
            "use_full_index": False,
            "comparison_type": "two_heroes",
            "comparison_heroes": list(two),
            "hero_filter": None,
            "top_k": 0,
            "confidence": "high",
        }

    # 1. RANKING — try deterministic stat tool first, fall back to full index
    if hero_id is None and _has_keyword(q, _RANKING_KW):
        stat = detect_stat_name(question)
        if stat:
            return {
                "collections": [],
                "use_full_index": False,
                "comparison_type": "rank_stat",
                "comparison_stat": stat,
                "hero_filter": None,
                "top_k": 0,
                "confidence": "high",
            }
        return {
            "collections": ["hero", "ability", "item"],
            "use_full_index": True,
            "comparison_type": None,
            "hero_filter": None,
            "top_k": FULL_INDEX_TOP_K,
            "confidence": "high",
        }

    # 2. ABILITIES (hero + ability keywords)
    if hero_id is not None and _has_keyword(q, _ABILITY_KW):
        return {
            "collections": ["ability"],
            "use_full_index": False,
            "hero_filter": hero_id,
            "top_k": 5,
            "confidence": "high",
        }

    # 3. FULL HERO INFO (hero + overview keywords)
    if hero_id is not None and _has_keyword(q, _OVERVIEW_KW):
        return {
            "collections": ["hero", "ability", "guide", "lore"],
            "use_full_index": False,
            "hero_filter": hero_id,
            "top_k": 8,
            "confidence": "high",
        }

    # 4. HERO LORE/STORY (hero + lore keywords)
    if hero_id is not None and _has_keyword(q, _LORE_KW):
        return {
            "collections": ["lore"],
            "use_full_index": False,
            "hero_filter": hero_id,
            "top_k": 5,
            "confidence": "high",
        }

    # 5. HERO STATS (hero + stats keywords)
    if hero_id is not None and _has_keyword(q, _STATS_KW):
        return {
            "collections": ["hero"],
            "use_full_index": False,
            "hero_filter": hero_id,
            "top_k": 3,
            "confidence": "high",
        }

    # 5. HERO MENTIONED (hero found, no other keyword match)
    if hero_id is not None:
        return {
            "collections": ["hero", "ability", "item"],
            "use_full_index": False,
            "hero_filter": hero_id,
            "top_k": 5,
            "confidence": "low",  # uncertain -- send to GPT
        }

    # 6. ITEMS (no hero, item keywords)
    if _has_keyword(q, _ITEM_KW):
        return {
            "collections": ["item"],
            "use_full_index": False,
            "hero_filter": None,
            "top_k": 4,
            "confidence": "high",
        }

    # 7. LORE
    if _has_keyword(q, _LORE_KW):
        return {
            "collections": ["lore"],
            "use_full_index": False,
            "hero_filter": hero_id,
            "top_k": 3,
            "confidence": "high",
        }

    # 8. GUIDES
    if _has_keyword(q, _GUIDE_KW):
        return {
            "collections": ["guide"],
            "use_full_index": False,
            "hero_filter": hero_id,
            "top_k": 3,
            "confidence": "high",
        }

    # 9. DEFAULT (nothing matched)
    return {
        "collections": ["hero", "ability", "item", "lore", "guide"],
        "use_full_index": False,
        "hero_filter": hero_id,
        "top_k": 3,
        "confidence": "low",  # uncertain -- send to GPT
    }


# ── Public API ───────────────────────────────────────────────────────────────

def route_query(question: str) -> dict:
    """
    Hybrid routing: keyword-first, GPT-4o-mini as fallback.

    Returns a dict with keys:
        collections (list[str]), use_full_index (bool),
        hero_filter (str|None), top_k (int), reasoning (str)
    """
    DEFAULT_ROUTE = {
        "collections": ["hero", "ability", "item"],
        "use_full_index": False,
        "hero_filter": None,
        "top_k": 3,
        "reasoning": "default fallback",
    }

    # Step 1 — keyword routing
    kw_result = keyword_route(question)
    confidence = kw_result.pop("confidence")

    if confidence == "high":
        kw_result["reasoning"] = "keyword routing"
        if os.getenv("DEBUG_ROUTER"):
            print(f"[router] keyword route: {kw_result}")
        return kw_result

    # Step 2 — GPT-4o-mini for uncertain cases
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        # No OpenAI key — use keyword result as fallback
        kw_result["reasoning"] = "keyword routing (no OpenAI key)"
        return kw_result

    try:
        if os.getenv("DEBUG_ROUTER"):
            print(f"[router] low confidence -> calling GPT-4o-mini")

        result = _call_router_llm(question)

        # validate
        assert isinstance(result.get("collections"), list)
        assert isinstance(result.get("top_k"), int)
        assert isinstance(result.get("use_full_index"), bool)
        result["top_k"] = max(1, min(FULL_INDEX_TOP_K, result["top_k"]))

        if os.getenv("DEBUG_ROUTER"):
            print(f"[router] GPT route: {result}")
        return result

    except Exception as e:
        if os.getenv("DEBUG_ROUTER"):
            print(f"[router] GPT failed: {e}, using keyword result")
        kw_result["reasoning"] = f"keyword fallback (GPT failed: {e})"
        return kw_result
