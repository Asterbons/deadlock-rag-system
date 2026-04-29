from src.rag import router


def test_keyword_route_ranking_queries_use_full_index():
    # No stat keyword, so falls through to the full-index fallback.
    route = router.keyword_route("Give me a hero tier list")

    assert route["use_full_index"] is True
    assert route["hero_filter"] is None
    assert route["top_k"] == 38
    assert route["collections"] == ["hero", "ability", "item"]


def test_keyword_route_hero_ability_queries_focus_ability_collection(monkeypatch):
    monkeypatch.setattr(router, "HERO_ALIASES", {"infernus": "hero_inferno"})

    route = router.keyword_route("What does Infernus ultimate do?")

    assert route["use_full_index"] is False
    assert route["hero_filter"] == "hero_inferno"
    assert route["top_k"] == 5
    assert route["collections"] == ["ability"]


def test_route_query_uses_keyword_fallback_when_openai_is_unavailable(monkeypatch):
    monkeypatch.setattr(router, "HERO_ALIASES", {"abrams": "hero_atlas"})
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    route = router.route_query("Abrams")

    assert route["hero_filter"] == "hero_atlas"
    assert route["collections"] == ["hero", "ability", "item"]
    assert route["top_k"] == 5
    assert route["reasoning"] == "keyword routing (no OpenAI key)"


# ── detect_two_heroes ────────────────────────────────────────────────────────

def test_detect_two_heroes_finds_pair_via_and():
    result = router.detect_two_heroes("compare infernus and seven")
    assert result is not None
    assert set(result) == {"hero_inferno", "hero_gigawatt"}


def test_detect_two_heroes_returns_none_for_single_hero():
    # Only one hero is mentioned — must not pick a second one out of thin air.
    assert router.detect_two_heroes("tell me about infernus") is None


def test_detect_two_heroes_returns_none_when_no_heroes():
    assert router.detect_two_heroes("how do I parry?") is None


# ── detect_stat_name ─────────────────────────────────────────────────────────

def test_detect_stat_name_basic_health():
    assert router.detect_stat_name("who has the most health") == "health"


def test_detect_stat_name_prefers_longer_match():
    # "bullet damage" must win over a hypothetical shorter "damage" key.
    assert router.detect_stat_name("highest bullet damage") == "bullet_damage"


def test_detect_stat_name_returns_none_for_non_stat_question():
    assert router.detect_stat_name("how do I play deadlock") is None


# ── keyword_route deterministic comparison paths ─────────────────────────────

def test_keyword_route_two_hero_comparison_uses_tool_path():
    route = router.keyword_route("compare infernus vs seven")

    assert route["comparison_type"] == "two_heroes"
    assert set(route["comparison_heroes"]) == {"hero_inferno", "hero_gigawatt"}
    assert route["use_full_index"] is False
    assert route["collections"] == []


def test_keyword_route_ranking_with_stat_uses_rank_tool():
    route = router.keyword_route("who has the highest health")

    assert route["comparison_type"] == "rank_stat"
    assert route["comparison_stat"] == "health"
    assert route["use_full_index"] is False
