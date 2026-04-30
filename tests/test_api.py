import json
import os

import pytest
from fastapi.testclient import TestClient

from src.api import server


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Point the server at a temporary processed/ directory with minimal fixture data."""
    data_dir = tmp_path / "processed"
    heroes_dir = data_dir / "heroes"
    heroes_dir.mkdir(parents=True)

    heroes_index = [
        {
            "hero": "hero_test",
            "hero_id": "hero_test",
            "name": "Test Hero",
            "hero_type": "Marksman",
            "complexity": 2,
        },
        {
            "hero": "hero_other",
            "hero_id": "hero_other",
            "name": "Other Hero",
            "hero_type": "Assassin",
            "complexity": 1,
        },
    ]
    (data_dir / "heroes_index.json").write_text(json.dumps(heroes_index), encoding="utf-8")

    test_hero_detail = {
        "hero_id": "hero_test",
        "name": "Test Hero",
        "abilities": [{"slot": 1, "name": "Arc Bolt"}],
    }
    (heroes_dir / "test_hero.json").write_text(json.dumps(test_hero_detail), encoding="utf-8")

    shop = {
        "weapon": [
            {"id": "item_w1", "name": "Basic Mag", "tier": 1, "slot": "weapon"},
            {"id": "item_w2", "name": "High-Velocity Mag", "tier": 2, "slot": "weapon"},
        ],
        "vitality": [
            {"id": "item_v1", "name": "Extra Health", "tier": 1, "slot": "vitality"},
        ],
        "spirit": [],
    }
    (data_dir / "shop.json").write_text(json.dumps(shop), encoding="utf-8")

    monkeypatch.setattr(server, "DATA_DIR", str(data_dir))
    return TestClient(server.app)


def test_health_check_returns_status_keys(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "llm" in body
    assert "qdrant" in body
    assert isinstance(body["llm"], bool)
    assert isinstance(body["qdrant"], bool)


def test_get_heroes_returns_full_index(client):
    resp = client.get("/api/heroes")
    assert resp.status_code == 200
    heroes = resp.json()
    assert len(heroes) == 2
    assert {h["hero"] for h in heroes} == {"hero_test", "hero_other"}


def test_get_heroes_filters_by_type(client):
    resp = client.get("/api/heroes", params={"type": "Marksman"})
    assert resp.status_code == 200
    heroes = resp.json()
    assert len(heroes) == 1
    assert heroes[0]["hero"] == "hero_test"


def test_get_hero_returns_detail_for_valid_id(client):
    resp = client.get("/api/heroes/hero_test")
    assert resp.status_code == 200
    body = resp.json()
    assert body["hero_id"] == "hero_test"
    assert body["abilities"][0]["name"] == "Arc Bolt"


def test_get_hero_returns_404_for_unknown_id(client):
    resp = client.get("/api/heroes/hero_does_not_exist")
    assert resp.status_code == 404


def test_get_hero_returns_404_when_detail_file_missing(client):
    # `hero_other` is in the index but has no corresponding detail file.
    resp = client.get("/api/heroes/hero_other")
    assert resp.status_code == 404


def test_get_items_returns_all_slots(client):
    resp = client.get("/api/items")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 3
    assert {i["id"] for i in items} == {"item_w1", "item_w2", "item_v1"}


def test_get_items_filters_by_slot(client):
    resp = client.get("/api/items", params={"slot": "weapon"})
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    assert all(i["slot"] == "weapon" for i in items)


def test_get_items_filters_by_tier(client):
    resp = client.get("/api/items", params={"tier": 1})
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    assert all(i["tier"] == 1 for i in items)


def test_get_item_returns_detail_for_valid_id(client):
    resp = client.get("/api/items/item_w2")
    assert resp.status_code == 200
    item = resp.json()
    assert item["name"] == "High-Velocity Mag"
    assert item["tier"] == 2


def test_get_item_returns_404_for_unknown_id(client):
    resp = client.get("/api/items/item_nope")
    assert resp.status_code == 404
