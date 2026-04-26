import io
import json

from src.rag import tools as rag_tools


def test_compare_hero_stat_ranks_fixture_data(monkeypatch):
    heroes_index = [
        {
            "name": "Alpha",
            "base_stats": {"health": 500},
            "weapon": {"bullet_damage": 40},
            "scaling_per_level": {"spirit_power": 1.2},
        },
        {
            "name": "Bravo",
            "base_stats": {"health": 650},
            "weapon": {"bullet_damage": 32},
            "scaling_per_level": {"spirit_power": 0.9},
        },
        {
            "name": "Charlie",
            "base_stats": {"health": 580},
            "weapon": {"bullet_damage": 45},
            "scaling_per_level": {"spirit_power": 1.5},
        },
    ]

    def fake_open(path, *args, **kwargs):
        assert path == "data/processed/heroes_index.json"
        return io.StringIO(json.dumps(heroes_index))

    monkeypatch.setattr(rag_tools, "open", fake_open, raising=False)

    result = rag_tools.compare_hero_stat.invoke({"stat_name": "health"})
    payload = json.loads(result)

    assert payload["stat"] == "health"
    assert payload["total_heroes"] == 3
    assert payload["ranking"][0] == {"hero": "Bravo", "value": 650, "rank": 1}
    assert payload["ranking"][-1] == {"hero": "Alpha", "value": 500, "rank": 3}


def test_compare_hero_stat_falls_back_to_weapon_and_scaling(monkeypatch):
    heroes_index = [
        {
            "name": "Alpha",
            "base_stats": {},
            "weapon": {"bullet_damage": 40},
            "scaling_per_level": {"spirit_power": 1.2},
        },
        {
            "name": "Bravo",
            "base_stats": {},
            "weapon": {"bullet_damage": 32},
            "scaling_per_level": {"spirit_power": 1.7},
        },
    ]

    def fake_open(path, *args, **kwargs):
        assert path == "data/processed/heroes_index.json"
        return io.StringIO(json.dumps(heroes_index))

    monkeypatch.setattr(rag_tools, "open", fake_open, raising=False)

    bullet_damage = json.loads(
        rag_tools.compare_hero_stat.invoke({"stat_name": "bullet_damage"})
    )
    spirit_power = json.loads(
        rag_tools.compare_hero_stat.invoke({"stat_name": "spirit_power"})
    )

    assert bullet_damage["ranking"][0]["hero"] == "Alpha"
    assert spirit_power["ranking"][0]["hero"] == "Bravo"


def test_compare_hero_stat_returns_error_for_unknown_metric(monkeypatch):
    def fake_open(path, *args, **kwargs):
        assert path == "data/processed/heroes_index.json"
        return io.StringIO(json.dumps([{"name": "Alpha"}]))

    monkeypatch.setattr(rag_tools, "open", fake_open, raising=False)

    result = rag_tools.compare_hero_stat.invoke({"stat_name": "not_a_real_stat"})
    payload = json.loads(result)

    assert payload == {"error": "Stat 'not_a_real_stat' not found"}
