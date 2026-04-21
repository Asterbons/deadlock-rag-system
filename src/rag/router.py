import json
import logging
import os
import sys

logger = logging.getLogger(__name__)

PROJ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

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

# ── Prompt for GPT-4o-mini fallback ──────────────────────────────────────────

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
  tier list, who has most/least) -> use_full_index: true
- Specific hero abilities -> collections: ["ability"],
  hero_filter: hero_id
- Build/item questions for a specific hero (e.g. "good items for X",
  "what should X buy", "best build for X") -> collections: ["hero", "ability", "item"],
  hero_filter: hero_id, top_k: 6
- General items/shop questions (no specific hero) -> collections: ["item"]
- Full hero overview -> collections: ["hero", "ability"],
  hero_filter: hero_id, top_k: 6
- General/mixed -> collections: ["hero", "ability", "item"], top_k: 3

Return ONLY valid JSON:
{{
  "collections": ["hero"|"ability"|"item"],
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
        hero_ids=hero_ids_string,
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


# ── Hero detection ───────────────────────────────────────────────────────────

def detect_hero(question: str) -> str | None:
    """Return the first hero_id whose alias appears in question, or None."""
    q = question.lower()
    for alias, hero_id in HERO_ALIASES.items():
        if alias in q:
            return hero_id
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


def _has_keyword(q: str, keywords: list[str]) -> bool:
    """Check if any keyword appears in the lowered question."""
    return any(kw in q for kw in keywords)


def keyword_route(question: str) -> dict:
    """
    Fast deterministic routing based on keyword matching.

    Returns a route dict with an extra "confidence" field:
        "high" — keyword match is strong, skip GPT
        "low"  — uncertain, GPT fallback recommended
    """
    q = question.lower()
    hero_id = detect_hero(question)

    # 1. RANKING (no hero, comparison of all)
    if hero_id is None and _has_keyword(q, _RANKING_KW):
        return {
            "collections": ["hero", "ability", "item"],
            "use_full_index": True,
            "hero_filter": None,
            "top_k": 38,
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
            "collections": ["hero", "ability"],
            "use_full_index": False,
            "hero_filter": hero_id,
            "top_k": 7,
            "confidence": "high",
        }

    # 4. HERO STATS (hero + stats keywords)
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

    # 7. DEFAULT (nothing matched)
    return {
        "collections": ["hero", "ability", "item"],
        "use_full_index": False,
        "hero_filter": None,
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
        result["top_k"] = max(1, min(38, result["top_k"]))

        if os.getenv("DEBUG_ROUTER"):
            print(f"[router] GPT route: {result}")
        return result

    except Exception as e:
        if os.getenv("DEBUG_ROUTER"):
            print(f"[router] GPT failed: {e}, using keyword result")
        kw_result["reasoning"] = f"keyword fallback (GPT failed: {e})"
        return kw_result
