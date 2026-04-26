import pytest
from src.shop_extractor.shop_builder import (
    _tier_to_int,
    _parse_numeric,
    _extract_stats,
    _extract_proc,
    _extract_synergies,
    _extract_upgrades,
    extract_items,
    build_shop_json,
    parse_localization,
)


class TestTierToInt:
    def test_standard_tier(self):
        assert _tier_to_int("EModTier_3") == 3

    def test_none_input(self):
        assert _tier_to_int(None) is None

    def test_non_string(self):
        assert _tier_to_int(123) is None

    def test_no_digit(self):
        assert _tier_to_int("EModTier_X") is None


class TestParseNumeric:
    def test_int(self):
        assert _parse_numeric(42) == 42

    def test_float(self):
        assert _parse_numeric(3.14) == 3.14

    def test_string_int(self):
        assert _parse_numeric("100") == 100

    def test_string_float(self):
        assert _parse_numeric("2.5") == 2.5

    def test_unit_suffix_stripped(self):
        assert _parse_numeric("150m") == 150

    def test_percent_suffix_stripped(self):
        assert _parse_numeric("25%") == 25

    def test_none_returns_none(self):
        assert _parse_numeric(None) is None

    def test_non_numeric_returns_none(self):
        assert _parse_numeric("abc") is None


class TestExtractStats:
    def test_extracts_valid_modifiers(self):
        props = {
            "TechPower": {
                "m_eProvidedPropertyType": "MODIFIER_VALUE_TECH_POWER",
                "m_strValue": "15",
            },
            "WeaponPower": {
                "m_eProvidedPropertyType": "MODIFIER_VALUE_WEAPON_POWER",
                "m_strValue": "0",
            },
        }
        result = _extract_stats(props)
        assert result.get("spirit_power") == 15
        # Zero values should be skipped
        assert "weapon_power" not in result

    def test_skips_invalid_modifiers(self):
        props = {
            "SomeProp": {
                "m_eProvidedPropertyType": "MODIFIER_VALUE_INVALID",
                "m_strValue": "10",
            },
        }
        assert _extract_stats(props) == {}


class TestExtractProc:
    def test_headshot_trigger(self):
        props = {
            "HeadShotBonusDamage": {
                "m_strValue": "25",
            },
        }
        proc = _extract_proc(props, "CITADEL_ABILITY_ACTIVATION_PASSIVE")
        assert proc is not None
        assert proc["trigger"] == "on_headshot"

    def test_on_hit_trigger(self):
        props = {
            "ProcChance": {
                "m_strValue": "30",
            },
            "ProcBonusMagicDamage": {
                "m_strValue": "25",
                "m_subclassScaleFunction": {
                    "_class": "scale_function_tech_damage",
                    "m_eSpecificStatScaleType": "ETechPower",
                    "m_flStatScale": 1.0,
                },
            },
        }
        proc = _extract_proc(props, "CITADEL_ABILITY_ACTIVATION_PASSIVE")
        assert proc is not None
        assert proc["trigger"] == "on_hit"
        assert proc["proc_chance_pct"] == 30
        assert "effects" in proc

    def test_aura_trigger(self):
        props = {
            "AuraRadius": {
                "m_strValue": "12m",
            },
            # Use BonusDamage (not in on_hit/headshot sets) so AuraRadius wins
            "BonusDamage": {
                "m_strValue": "10",
                "m_subclassScaleFunction": {
                    "_class": "scale_function_tech_damage",
                    "m_eSpecificStatScaleType": "ETechPower",
                    "m_flStatScale": 0.5,
                },
            },
        }
        proc = _extract_proc(props, "CITADEL_ABILITY_ACTIVATION_PASSIVE")
        assert proc is not None
        assert proc["trigger"] == "aura"
        assert "effects" in proc

    def test_on_cast_trigger(self):
        props = {}
        proc = _extract_proc(props, "CITADEL_ABILITY_ACTIVATION_PRESS")
        assert proc is not None
        assert proc["trigger"] == "on_cast"

    def test_no_trigger(self):
        props = {}
        proc = _extract_proc(props, "CITADEL_ABILITY_ACTIVATION_UNKNOWN")
        assert proc is None

    def test_cooldown_extraction(self):
        props = {
            "AbilityCooldown": {
                "m_strValue": "12.5",
            },
        }
        proc = _extract_proc(props, "CITADEL_ABILITY_ACTIVATION_INSTANT_CAST")
        assert proc["item_cooldown_sec"] == 12.5


class TestExtractSynergies:
    def test_provides_and_scales_with(self):
        props = {
            "TechPower": {
                "m_eProvidedPropertyType": "MODIFIER_VALUE_TECH_POWER",
                "m_strValue": "10",
                "m_subclassScaleFunction": {
                    "m_eSpecificStatScaleType": "ETechPower",
                },
            },
        }
        result = _extract_synergies(props)
        assert "spirit_power" in result["provides"]
        assert "spirit_power" in result["scales_with"]

    def test_empty_for_zero_values(self):
        props = {
            "TechPower": {
                "m_eProvidedPropertyType": "MODIFIER_VALUE_TECH_POWER",
                "m_strValue": "0",
            },
        }
        result = _extract_synergies(props)
        assert result["provides"] == []
        assert result["scales_with"] == []


class TestExtractUpgrades:
    def test_single_upgrade_block(self):
        item_data = {
            "m_vecAbilityUpgrades": {
                "m_vecPropertyUpgrades": [
                    {"m_strPropertyName": "AbilityCooldown", "m_strBonus": "-2"},
                ],
            },
        }
        result = _extract_upgrades(item_data)
        # _normalize_property_name prefixes with "ability_"
        assert result == {"ability_cooldown_bonus": -2}

    def test_list_of_upgrade_blocks(self):
        item_data = {
            "m_vecAbilityUpgrades": [
                {
                    "m_vecPropertyUpgrades": [
                        {"m_strPropertyName": "AbilityDuration", "m_strBonus": "1.5"},
                    ],
                },
            ],
        }
        result = _extract_upgrades(item_data)
        assert result == {"ability_duration_bonus": 1.5}

    def test_no_upgrades(self):
        assert _extract_upgrades({}) is None

    def test_empty_upgrade_list(self):
        assert _extract_upgrades({"m_vecAbilityUpgrades": []}) is None


class TestExtractItems:
    def test_skips_non_items(self):
        parsed = {
            "ability_fireball": {
                "m_eAbilityType": "EAbilityType_HeroAbility",
            },
        }
        loc = {"display_names": {}, "descriptions": {}}
        assert extract_items(parsed, loc) == []

    def test_skips_disabled_items(self):
        parsed = {
            "upgrade_test": {
                "m_eAbilityType": "EAbilityType_Item",
                "m_bDisabled": True,
            },
        }
        loc = {"display_names": {}, "descriptions": {}}
        assert extract_items(parsed, loc) == []

    def test_skips_template_items(self):
        parsed = {
            "weapon_upgrade_t1": {
                "m_eAbilityType": "EAbilityType_Item",
                "m_bDisabled": False,
            },
        }
        loc = {"display_names": {}, "descriptions": {}}
        assert extract_items(parsed, loc) == []

    def test_extracts_valid_item(self):
        parsed = {
            "upgrade_test_item": {
                "m_eAbilityType": "EAbilityType_Item",
                "m_bDisabled": False,
                "m_iItemTier": "EModTier_2",
                "m_eItemSlotType": "EItemSlotType_WeaponMod",
                "m_eAbilityActivation": "CITADEL_ABILITY_ACTIVATION_PASSIVE",
                "m_mapAbilityProperties": {
                    "WeaponPower": {
                        "m_eProvidedPropertyType": "MODIFIER_VALUE_WEAPON_POWER",
                        "m_strValue": "8",
                    },
                },
            },
        }
        loc = {
            "display_names": {"upgrade_test_item": "Test Item"},
            "descriptions": {},
        }
        items = extract_items(parsed, loc)
        assert len(items) == 1
        item = items[0]
        assert item["id"] == "upgrade_test_item"
        assert item["name"] == "Test Item"
        assert item["tier"] == 2
        assert item["slot"] == "weapon"
        assert item["passive"] is True
        assert item["stats"]["weapon_power"] == 8

    def test_fallback_name_formatting(self):
        parsed = {
            "upgrade_cool_reduction": {
                "m_eAbilityType": "EAbilityType_Item",
                "m_bDisabled": False,
                "m_iItemTier": "EModTier_1",
                "m_eItemSlotType": "EItemSlotType_Tech",
                "m_eAbilityActivation": "CITADEL_ABILITY_ACTIVATION_PASSIVE",
                "m_mapAbilityProperties": {},
            },
        }
        loc = {"display_names": {}, "descriptions": {}}
        items = extract_items(parsed, loc)
        assert items[0]["name"] == "Cool Reduction"


class TestBuildShopJson:
    def test_assembles_structure(self):
        items = [
            {"id": "item_a", "slot": "weapon", "tier": 1, "upgrades_from": []},
            {"id": "item_b", "slot": "spirit", "tier": 2, "upgrades_from": []},
            {"id": "item_c", "slot": "vitality", "tier": 3, "upgrades_from": []},
        ]
        bonuses = {}
        shop = build_shop_json(items, bonuses)
        assert len(shop["weapon"]) == 1
        assert len(shop["spirit"]) == 1
        assert len(shop["vitality"]) == 1

    def test_sorts_by_tier(self):
        items = [
            {"id": "item_b", "slot": "weapon", "tier": 3, "upgrades_from": []},
            {"id": "item_a", "slot": "weapon", "tier": 1, "upgrades_from": []},
            {"id": "item_c", "slot": "weapon", "tier": 2, "upgrades_from": []},
        ]
        shop = build_shop_json(items, {})
        tiers = [i["tier"] for i in shop["weapon"]]
        assert tiers == [1, 2, 3]

    def test_upgrades_into_linked(self):
        items = [
            {"id": "base_item", "slot": "weapon", "tier": 1, "upgrades_from": []},
            {"id": "advanced_item", "slot": "weapon", "tier": 2, "upgrades_from": ["base_item"]},
        ]
        shop = build_shop_json(items, {})
        base = shop["weapon"][0]
        assert base["upgrades_into"] == "advanced_item"

    def test_renames_tech_to_spirit_in_bonuses(self):
        items = []
        bonuses = {"tech": [{"net_worth": 1000, "value": 5, "type": "spirit_power"}]}
        shop = build_shop_json(items, bonuses)
        assert "tech" not in shop["global_mechanics"]["purchase_bonuses"]
        assert "spirit" in shop["global_mechanics"]["purchase_bonuses"]


class TestParseLocalization:
    def test_display_names_from_comments(self, tmp_path):
        filepath = tmp_path / "mods.txt"
        filepath.write_text(
            "// Test Item\n"
            '"upgrade_test_desc" "Does something cool."\n',
            encoding="utf-8",
        )
        result = parse_localization(filepath)
        assert result["display_names"]["upgrade_test"] == "Test Item"
        assert result["descriptions"]["upgrade_test"] == "Does something cool."

    def test_comment_with_quotes_format(self, tmp_path):
        filepath = tmp_path / "mods.txt"
        filepath.write_text(
            '// "upgrade_special" "Special Item"\n'
            '"upgrade_special_desc" "Very special."\n',
            encoding="utf-8",
        )
        result = parse_localization(filepath)
        assert result["display_names"]["upgrade_special"] == "Special Item"

    def test_comment_with_dash_format(self, tmp_path):
        filepath = tmp_path / "mods.txt"
        filepath.write_text(
            "// Fireball - upgrade_fireball\n"
            '"upgrade_fireball_desc" "Throws a fireball."\n',
            encoding="utf-8",
        )
        result = parse_localization(filepath)
        assert result["display_names"].get("upgrade_fireball") == "Fireball"

    def test_skips_dash_only_comments(self, tmp_path):
        filepath = tmp_path / "mods.txt"
        filepath.write_text(
            "// ---\n"
            '"upgrade_test_desc" "Desc."\n',
            encoding="utf-8",
        )
        result = parse_localization(filepath)
        # No comment name should be tracked after a dash-only line
        assert "upgrade_test" not in result["display_names"]
