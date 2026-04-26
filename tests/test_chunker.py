import json

from src.rag.chunker import chunk_heroes


def test_chunk_heroes_emits_stats_build_and_ability_chunks(tmp_path):
    index_path = tmp_path / "heroes_index.json"
    heroes_dir = tmp_path / "heroes"
    heroes_dir.mkdir()

    index_payload = [
        {
            "hero": "hero_test",
            "hero_id": "hero_test",
            "name": "Test Hero",
            "hero_type": "Marksman",
            "complexity": 2,
            "image": "https://example.com/hero.png",
            "good_items": [{"name": "Mystic Shot"}, {"name": "Fleetfoot"}],
            "tags": {
                "damage_type": ["Spirit"],
                "utility": ["Slow"],
                "playstyle": ["Poke"],
                "flavor": ["Sniper"],
            },
            "base_stats": {
                "health": 600,
                "max_move_speed": 7.1,
            },
            "weapon": {
                "bullet_damage": 42,
                "bullet_speed": 180,
                "rounds_per_sec": 2.5,
                "clip_size": 10,
                "can_zoom": True,
            },
            "scaling_per_level": {
                "health": 20,
                "spirit_power": 1.5,
            },
            "abilities": [
                {
                    "slot": 1,
                    "effect_types": ["damage", "slow"],
                }
            ],
        }
    ]
    index_path.write_text(json.dumps(index_payload), encoding="utf-8")

    hero_details = {
        "hero_id": "hero_test",
        "abilities": [
            {
                "id": "ability_test_1",
                "name": "Arc Bolt",
                "slot": 1,
                "cast_type": "targeted",
                "targeting": "enemy",
                "description": "Throw a charged projectile.",
                "image": "https://example.com/ability.png",
                "stats": {
                    "cooldown": 8.0,
                    "ability_unit_target_limit": 3,
                },
                "effects": [
                    {"type": "damage", "formula": "120 + 0.8x Spirit"},
                    {"type": "slow", "base_value": 25, "unit": "%"},
                    {"type": "ignored", "base_value": 0},
                ],
                "upgrades": [
                    {"description": "+1 bounce"},
                ],
            }
        ],
    }
    (heroes_dir / "hero_test.json").write_text(
        json.dumps(hero_details),
        encoding="utf-8",
    )

    chunks = chunk_heroes(str(index_path), str(heroes_dir))

    assert [chunk["metadata"]["type"] for chunk in chunks] == [
        "hero",
        "hero_build",
        "ability",
    ]

    stats_chunk, build_chunk, ability_chunk = chunks

    assert "move_speed: 7.1" in stats_chunk["text"]
    assert stats_chunk["metadata"]["hero_id"] == "hero_test"
    assert stats_chunk["metadata"]["image"] == "https://example.com/hero.png"

    assert "good items: Mystic Shot, Fleetfoot" in build_chunk["text"]
    assert "playstyle: Poke" in build_chunk["text"]
    assert build_chunk["metadata"]["type"] == "hero_build"

    assert "stats: {'cooldown': 8}" in ability_chunk["text"]
    assert "ability_unit_target_limit" not in ability_chunk["text"]
    assert "effects: damage: 120 + 0.8x Spirit, slow: 25%" in ability_chunk["text"]
    assert "upgrades: +1 bounce" in ability_chunk["text"]
    assert ability_chunk["metadata"]["ability_id"] == "ability_test_1"
    assert ability_chunk["metadata"]["image"] == "https://example.com/ability.png"
    assert ability_chunk["metadata"]["effect_types"] == ["damage", "slow"]
