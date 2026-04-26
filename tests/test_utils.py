import pytest
from src.heroes_abilities_extractor.utils import (
    camel_to_snake,
    normalize,
    strip_html,
    clean_description,
    get_stat_name,
)


class TestCamelToSnake:
    def test_simple(self):
        assert camel_to_snake("CamelCase") == "camel_case"

    def test_all_caps_prefix(self):
        assert camel_to_snake("HTTPResponse") == "http_response"

    def test_numbers(self):
        assert camel_to_snake("Test123Case") == "test123_case"

    def test_already_snake(self):
        assert camel_to_snake("snake_case") == "snake_case"

    def test_multiple_underscores_collapsed(self):
        assert camel_to_snake("A__B") == "a_b"

    def test_leading_trailing_underscores_stripped(self):
        assert camel_to_snake("_Test_") == "test"


class TestNormalize:
    def test_none_returns_zero(self):
        assert normalize(None) == 0

    def test_int_passthrough(self):
        assert normalize(42) == 42

    def test_float_rounding(self):
        assert normalize(3.14159265) == 3.141593

    def test_float_to_int_when_whole(self):
        assert normalize(5.0) == 5

    def test_string_numeric(self):
        assert normalize("  123  ") == 123

    def test_string_float(self):
        assert normalize("3.5") == 3.5

    def test_non_numeric_string(self):
        assert normalize("hello") == "hello"


class TestStripHtml:
    def test_removes_tags(self):
        assert strip_html("<b>Bold</b>") == "Bold"

    def test_removes_br(self):
        # <br> is stripped by the regex before the replace runs
        assert strip_html("Line1<br>Line2") == "Line1Line2"

    def test_removes_g_tokens(self):
        assert strip_html("{g:citadel_inline_attribute:'Damage'}") == ""

    def test_empty_input(self):
        assert strip_html("") == ""

    def test_none_input(self):
        assert strip_html(None) == ""

    def test_mixed_content(self):
        text = '<span class="highlight">Hello</span> <br> World'
        assert strip_html(text) == "Hello  World"


class TestCleanDescription:
    def test_empty(self):
        assert clean_description("", {}) == ""

    def test_inline_attribute_replacement(self):
        text = "Deals {g:citadel_inline_attribute:'Damage'} damage"
        inline_attrs = {"Damage": "120"}
        assert clean_description(text, inline_attrs) == "Deals 120 damage"

    def test_binding_replacement(self):
        text = "Press {g:citadel_binding:'Ability1'} to cast"
        assert clean_description(text, {}) == "Press [Ability1] to cast"

    def test_stat_placeholder_replaced_with_x(self):
        text = "Deals {s:AbilityDamage} damage"
        assert clean_description(text, {}) == "Deals X damage"

    def test_html_stripped(self):
        text = "<b>Bold</b> text"
        assert clean_description(text, {}) == "Bold text"

    def test_collapse_spaces(self):
        text = "Too    many     spaces"
        assert clean_description(text, {}) == "Too many spaces"

    def test_unknown_inline_attr_falls_back_to_key(self):
        text = "{g:citadel_inline_attribute:'Missing'}"
        assert clean_description(text, {}) == "missing"


class TestGetStatName:
    def test_stat_label_lookup(self):
        stat_labels = {
            "m_MoveSpeed": {"label": "Movement Speed", "unit": "m/s"},
        }
        assert get_stat_name("m_MoveSpeed", stat_labels) == "movement_speed"

    def test_mapping_fallback(self):
        # MAPPING falls back to camel_to_snake if key not found;
        # for "m_Health" this yields "m_health"
        result = get_stat_name("m_Health")
        assert result == "m_health"

    def test_unknown_key_returns_snake(self):
        result = get_stat_name("m_UnknownStat")
        # MAPPING will fall back to camel_to_snake-like behavior
        assert "unknown" in result
