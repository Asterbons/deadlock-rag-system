import pytest
from src.heroes_abilities_extractor.localization import (
    resolve_ability_name,
    parse_localization,
)


class TestResolveAbilityName:
    def test_exact_match(self):
        names = {"ability_fireball": "Fireball"}
        assert resolve_ability_name("ability_fireball", names) == "Fireball"

    def test_citadel_prefix_replacement(self):
        names = {"ability_fireball": "Fireball"}
        assert resolve_ability_name("citadel_ability_fireball", names) == "Fireball"

    def test_suffix_match(self):
        names = {"some_prefix_fireball": "Fireball"}
        assert resolve_ability_name("ability_fireball", names) == "Fireball"

    def test_fallback_title_case(self):
        names = {}
        result = resolve_ability_name("citadel_ability_dark_matter", names)
        assert result == "Dark Matter"

    def test_exact_last_segment_match(self):
        names = {"heal": "Healing Wave"}
        assert resolve_ability_name("ability_heal", names) == "Healing Wave"


class TestParseLocalization:
    def test_hero_names_extracted(self, tmp_path):
        hero_names = tmp_path / "hero_names.txt"
        heroes = tmp_path / "heroes.txt"
        attrs = tmp_path / "attrs.txt"

        hero_names.write_text('"hero_inferno" "Infernus"\n', encoding="utf-8")
        heroes.write_text("", encoding="utf-8")
        attrs.write_text("", encoding="utf-8")

        loc = parse_localization(str(hero_names), str(heroes), str(attrs))
        assert loc["hero_names"]["hero_inferno"] == "Infernus"

    def test_ability_names_and_descs(self, tmp_path):
        hero_names = tmp_path / "hero_names.txt"
        heroes = tmp_path / "heroes.txt"
        attrs = tmp_path / "attrs.txt"

        hero_names.write_text("", encoding="utf-8")
        heroes.write_text(
            '"ability_fireball" "Fireball"\n'
            '"ability_fireball_desc" "Throws a fireball."\n',
            encoding="utf-8",
        )
        attrs.write_text("", encoding="utf-8")

        loc = parse_localization(str(hero_names), str(heroes), str(attrs))
        assert loc["ability_names"]["ability_fireball"] == "Fireball"
        assert loc["ability_descs"]["ability_fireball"] == "Throws a fireball."

    def test_upgrade_descs_concatenated(self, tmp_path):
        hero_names = tmp_path / "hero_names.txt"
        heroes = tmp_path / "heroes.txt"
        attrs = tmp_path / "attrs.txt"

        hero_names.write_text("", encoding="utf-8")
        heroes.write_text(
            '"upgrade_fireball_t1_desc" "+20 Damage"\n'
            '"upgrade_fireball_t1_desc_2" "+1 Range"\n',
            encoding="utf-8",
        )
        attrs.write_text("", encoding="utf-8")

        loc = parse_localization(str(hero_names), str(heroes), str(attrs))
        assert "+20 Damage" in loc["upgrade_descs"]["upgrade_fireball_t1"]
        assert "+1 Range" in loc["upgrade_descs"]["upgrade_fireball_t1"]

    def test_stat_labels_from_attributes(self, tmp_path):
        hero_names = tmp_path / "hero_names.txt"
        heroes = tmp_path / "heroes.txt"
        attrs = tmp_path / "attrs.txt"

        hero_names.write_text("", encoding="utf-8")
        heroes.write_text("", encoding="utf-8")
        attrs.write_text(
            '"StatDesc_MoveSpeed" "Movement Speed"\n'
            '"MoveSpeed_label" "Move Speed"\n'
            '"StatDesc_MoveSpeed_postfix" "m/s"\n',
            encoding="utf-8",
        )

        loc = parse_localization(str(hero_names), str(heroes), str(attrs))
        # MoveSpeed_label overwrites StatDesc_MoveSpeed in the second pass
        assert loc["stat_labels"]["MoveSpeed"]["label"] == "Move Speed"
        assert loc["stat_labels"]["MoveSpeed"]["unit"] == "m/s"

    def test_inline_attrs_extracted(self, tmp_path):
        hero_names = tmp_path / "hero_names.txt"
        heroes = tmp_path / "heroes.txt"
        attrs = tmp_path / "attrs.txt"

        hero_names.write_text("", encoding="utf-8")
        heroes.write_text("", encoding="utf-8")
        attrs.write_text(
            '"InlineAttribute_Damage" "Damage"\n',
            encoding="utf-8",
        )

        loc = parse_localization(str(hero_names), str(heroes), str(attrs))
        assert loc["inline_attrs"]["Damage"] == "Damage"
        assert loc["effect_types"]["damage"] == "Damage"

    def test_effect_types_from_modifier_state(self, tmp_path):
        hero_names = tmp_path / "hero_names.txt"
        heroes = tmp_path / "heroes.txt"
        attrs = tmp_path / "attrs.txt"

        hero_names.write_text("", encoding="utf-8")
        heroes.write_text("", encoding="utf-8")
        attrs.write_text(
            '"MODIFIER_STATE_STUNNED" "Stunned"\n',
            encoding="utf-8",
        )

        loc = parse_localization(str(hero_names), str(heroes), str(attrs))
        assert loc["effect_types"]["stunned"] == "Stunned"

    def test_hero_tags_extracted(self, tmp_path):
        hero_names = tmp_path / "hero_names.txt"
        heroes = tmp_path / "heroes.txt"
        attrs = tmp_path / "attrs.txt"

        hero_names.write_text("", encoding="utf-8")
        heroes.write_text(
            '"Citadel_Inferno_HeroTag_1" "DPS"\n'
            '"Citadel_Inferno_HeroTag_2" "Fire"\n',
            encoding="utf-8",
        )
        attrs.write_text("", encoding="utf-8")

        loc = parse_localization(str(hero_names), str(heroes), str(attrs))
        assert "inferno" in loc["hero_tags_by_keyword"]
        assert loc["hero_tags_by_keyword"]["inferno"] == ["DPS", "Fire"]

    def test_skips_comments(self, tmp_path):
        hero_names = tmp_path / "hero_names.txt"
        heroes = tmp_path / "heroes.txt"
        attrs = tmp_path / "attrs.txt"

        hero_names.write_text(
            '// This is a comment\n"hero_test" "Test Hero"\n',
            encoding="utf-8",
        )
        heroes.write_text("", encoding="utf-8")
        attrs.write_text("", encoding="utf-8")

        loc = parse_localization(str(hero_names), str(heroes), str(attrs))
        assert loc["hero_names"]["hero_test"] == "Test Hero"

    def test_missing_files_graceful(self, tmp_path):
        hero_names = tmp_path / "missing.txt"
        heroes = tmp_path / "missing2.txt"
        attrs = tmp_path / "missing3.txt"

        loc = parse_localization(str(hero_names), str(heroes), str(attrs))
        assert loc["hero_names"] == {}
        assert loc["ability_names"] == {}
