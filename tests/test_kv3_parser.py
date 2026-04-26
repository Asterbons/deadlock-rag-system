import pytest
from src.heroes_abilities_extractor.kv3_parser import parse_kv3, _normalise


class TestNormalise:
    def test_boolean_true(self):
        assert _normalise("true") is True

    def test_boolean_false(self):
        assert _normalise("false") is False

    def test_integer(self):
        assert _normalise("42") == 42

    def test_float(self):
        assert _normalise("3.14") == 3.14

    def test_float_trailing_zeros(self):
        assert _normalise("6.700000") == 6.7

    def test_scientific_notation(self):
        assert _normalise("1e3") == 1000

    def test_quoted_string(self):
        assert _normalise('"hello world"') == "hello world"

    def test_empty_string(self):
        assert _normalise("") == ""

    def test_whitespace_only(self):
        assert _normalise("   ") == ""


class TestParseKV3Basic:
    def test_empty_dict(self):
        assert parse_kv3("{}") == {}

    def test_simple_key_value(self):
        text = '{"key" "value"}'
        assert parse_kv3(text) == {"key": "value"}

    def test_colon_assignment(self):
        text = '{"key": "value"}'
        assert parse_kv3(text) == {"key": "value"}

    def test_equals_assignment(self):
        text = '{"key" = "value"}'
        assert parse_kv3(text) == {"key": "value"}

    def test_numeric_value(self):
        text = '{"health" 600}'
        assert parse_kv3(text) == {"health": 600}

    def test_boolean_value(self):
        text = '{"disabled" true}'
        assert parse_kv3(text) == {"disabled": True}


class TestParseKV3Nested:
    def test_nested_dict(self):
        text = """
        {
            "hero" {
                "name" "Infernus"
                "health" 550
            }
        }
        """
        result = parse_kv3(text)
        assert result == {"hero": {"name": "Infernus", "health": 550}}

    def test_deep_nesting(self):
        text = """
        {
            "a" {
                "b" {
                    "c" {
                        "d" 1
                    }
                }
            }
        }
        """
        result = parse_kv3(text)
        assert result["a"]["b"]["c"]["d"] == 1

    def test_list_value(self):
        text = '{"items" ["sword" "shield" "potion"]}'
        assert parse_kv3(text) == {"items": ["sword", "shield", "potion"]}

    def test_mixed_list(self):
        text = '{"stats" [1 2.5 true "text"]}'
        assert parse_kv3(text) == {"stats": [1, 2.5, True, "text"]}

    def test_empty_list(self):
        text = '{"items" []}'
        assert parse_kv3(text) == {"items": []}


class TestParseKV3Comments:
    def test_line_comment(self):
        text = """
        {
            // this is a comment
            "key" "value"
        }
        """
        assert parse_kv3(text) == {"key": "value"}

    def test_block_comment(self):
        text = """
        {
            /* block
               comment */
            "key" "value"
        }
        """
        assert parse_kv3(text) == {"key": "value"}

    def test_xml_header_stripped(self):
        text = """
        <!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->
        {
            "key" "value"
        }
        """
        assert parse_kv3(text) == {"key": "value"}


class TestParseKV3ValvePrefixes:
    def test_resource_name_prefix(self):
        text = '{"icon" resource_name:"images/heroes/infernus.png"}'
        assert parse_kv3(text) == {"icon": "images/heroes/infernus.png"}

    def test_panorama_prefix(self):
        text = '{"image" panorama:"file://{images}/hero.png"}'
        assert parse_kv3(text) == {"image": "file://{images}/hero.png"}

    def test_soundevent_prefix(self):
        text = '{"sound" soundevent:"Hero.Infernus.Attack"}'
        assert parse_kv3(text) == {"sound": "Hero.Infernus.Attack"}

    def test_subclass_prefix_with_brace(self):
        text = '{"data" subclass: {"inner" 1}}'
        assert parse_kv3(text) == {"data": {"inner": 1}}


class TestParseKV3EdgeCases:
    def test_trailing_comma_in_list(self):
        text = '{"items" [1, 2, 3, ]}'
        assert parse_kv3(text) == {"items": [1, 2, 3]}

    def test_no_outer_braces(self):
        text = '"key1" "val1" "key2" "val2"'
        assert parse_kv3(text) == {"key1": "val1", "key2": "val2"}

    def test_escaped_quotes_in_string(self):
        text = r'{"desc" "Say \"hello\" to them"}'
        assert parse_kv3(text) == {"desc": 'Say "hello" to them'}

    def test_multiple_top_level_blocks(self):
        text = """
        "hero_base" {
            "health" 500
        }
        "hero_inferno" {
            "health" 550
        }
        """
        result = parse_kv3(text)
        assert result["hero_base"]["health"] == 500
        assert result["hero_inferno"]["health"] == 550

    def test_stray_closing_brace_at_root(self):
        text = '"key" "value" }'
        assert parse_kv3(text) == {"key": "value"}

    def test_empty_inline_dict(self):
        text = '{"data" {}}'
        assert parse_kv3(text) == {"data": {}}

    def test_empty_inline_list(self):
        text = '{"data" []}'
        assert parse_kv3(text) == {"data": []}

    def test_multiline_block_with_brace_on_next_line(self):
        text = """
        {
            "nested"
            {
                "key" "value"
            }
        }
        """
        assert parse_kv3(text) == {"nested": {"key": "value"}}

    def test_pipe_separated_enum_in_quotes(self):
        text = '{"flags" "FLAG_A | FLAG_B | FLAG_C"}'
        assert parse_kv3(text) == {"flags": "FLAG_A | FLAG_B | FLAG_C"}
