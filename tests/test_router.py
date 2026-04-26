from src.rag import router


def test_keyword_route_ranking_queries_use_full_index():
    route = router.keyword_route("Who has the highest health in the game?")

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
