import os
import re
import logging
import sys
from pathlib import Path
from utils import strip_html, camel_to_snake

logger = logging.getLogger(__name__)

def resolve_ability_name(ability_id: str, ability_names: dict) -> str:
    """Multi-step ability name resolution.

    1. Exact match on ability_id
    2. Try replacing 'citadel_ability_' prefix with 'ability_'
    3. Any key that ends with the last segment of ability_id
    4. Fallback: strip prefix, replace _ with space, title-case  (logs WARNING)
    """
    # Step 1: exact match
    name = ability_names.get(ability_id)
    if name:
        return name

    # Step 2: alternate prefix
    alt_key = ability_id.replace("citadel_ability_", "ability_")
    name = ability_names.get(alt_key)
    if name:
        return name

    # Step 3: suffix match — last segment after the last '_'
    last_segment = ability_id.rsplit("_", 1)[-1]
    for k, v in ability_names.items():
        if k.endswith("_" + last_segment) or k == last_segment:
            return v

    # Step 4: synthetic fallback
    fallback = ability_id
    for prefix in ("citadel_ability_", "ability_"):
        if fallback.startswith(prefix):
            fallback = fallback[len(prefix):]
            break
    fallback = fallback.replace("_", " ").title()
    logger.warning("Ability name not found in localization for '%s', using fallback '%s'", ability_id, fallback)
    return fallback

def parse_localization(hero_names_path, heroes_english_path, attributes_english_path, mods_english_path=None):
    loc = {
        "hero_names": {},
        "ability_names": {},
        "ability_descs": {},
        "upgrade_descs": {},
        "hero_tags_by_keyword": {},
        "stat_labels": {},
        "inline_attrs": {},
        "mod_names": {},
        "effect_types": {}
    }

    def load_vdf_tokens(path):
        if not path or not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            tokens = {}
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("//"):
                    continue
                match = re.search(r'"([^"]+)"\s*"(.*?(?<!\\))"', stripped)
                if match:
                    tokens[match.group(1)] = match.group(2)
            return tokens
        except Exception as e:
            print(f"Error loading {path}: {e}")
            return {}

    # 1. Hero Names
    hero_names_tokens = load_vdf_tokens(hero_names_path)
    for k, v in hero_names_tokens.items():
        if ":" in k: k = k.split(":")[0]
        if k.startswith("hero_") and not k.endswith("_desc"):
             loc["hero_names"][k] = v

    # 2. Heroes English
    heroes_tokens = load_vdf_tokens(heroes_english_path)
    for k, v in heroes_tokens.items():
        if k.startswith("Citadel_"):
             m = re.match(r"Citadel_(.+)_HeroTag_\d", k)
             if m:
                 tag_key = m.group(1).lower()
                 if tag_key not in loc["hero_tags_by_keyword"]:
                     loc["hero_tags_by_keyword"][tag_key] = []
                 loc["hero_tags_by_keyword"][tag_key].append(v)
        elif re.search(r"_desc(?:_\d+)?$", k):
            if re.search(r"_t[1-3]_desc(?:_\d+)?$", k):
                key = re.sub(r"_desc(?:_\d+)?$", "", k)
                if key in loc["upgrade_descs"]:
                    loc["upgrade_descs"][key] += " | " + v
                else:
                    loc["upgrade_descs"][key] = v
            else:
                key = re.sub(r"_desc(?:_\d+)?$", "", k)
                if key in loc["ability_descs"]:
                    loc["ability_descs"][key] += " | " + v
                else:
                    loc["ability_descs"][key] = v
        elif not k.endswith("_quip"):
            if k.endswith("_label"):
                stat_name = k.replace("_label", "")
                if stat_name not in loc["stat_labels"]:
                    loc["stat_labels"][stat_name] = {"label": strip_html(v), "unit": ""}
                else:
                    loc["stat_labels"][stat_name]["label"] = strip_html(v)
            else:
                loc["ability_names"][k] = strip_html(v)

    # 3. Attributes English
    attr_tokens = load_vdf_tokens(attributes_english_path)
    for k, v in attr_tokens.items():
        if k.startswith("StatDesc_") and not k.endswith("_postfix") and not k.endswith("_prefix") and not k.endswith("_label"):
            stat_name = k.replace("StatDesc_", "")
            loc["stat_labels"][stat_name] = {"label": strip_html(v), "unit": ""}
        elif k.startswith("InlineAttribute_"):
            attr_name = k.replace("InlineAttribute_", "")
            clean_v = strip_html(v)
            loc["inline_attrs"][attr_name] = clean_v
            
            clean_eff = camel_to_snake(attr_name)
            if clean_eff == "heals": clean_eff = "heal"
            if clean_eff == "pulls": clean_eff = "pull"
            if clean_eff == "toss": clean_eff = "knockup"
            if clean_eff:
                loc["effect_types"][clean_eff] = clean_v
            
        elif k.startswith("MODIFIER_STATE_"):
            clean_eff = k.replace("MODIFIER_STATE_", "").lower()
            if clean_eff:
                loc["effect_types"][clean_eff] = strip_html(v)
            
        elif k.startswith("Citadel_StatusEffect"):
            attr_name = k.replace("Citadel_StatusEffect", "")
            clean_eff = camel_to_snake(attr_name)
            if clean_eff:
                loc["effect_types"][clean_eff] = strip_html(v)
            
    for k, v in attr_tokens.items():
         if k.endswith("_label"):
             stat_name = k.replace("_label", "")
             if stat_name not in loc["stat_labels"]:
                 loc["stat_labels"][stat_name] = {"label": strip_html(v), "unit": ""}
             else:
                 loc["stat_labels"][stat_name]["label"] = strip_html(v)
         elif k.startswith("StatDesc_") and k.endswith("_postfix"):
             stat_name = k.replace("StatDesc_", "").replace("_postfix", "")
             if stat_name in loc["stat_labels"]:
                 loc["stat_labels"][stat_name]["unit"] = v.strip()

    # 4. Mod Names
    if mods_english_path:
        shop_dir = Path(__file__).parent.parent / "shop_extractor"
        if str(shop_dir) not in sys.path:
            sys.path.insert(0, str(shop_dir))
        try:
            import shop_builder
            shop_loc = shop_builder.parse_localization(mods_english_path)
            loc["mod_names"] = shop_loc.get("display_names", {})
        except Exception as e:
            print(f"Error loading shop_builder: {e}")

    # Explicit aliases and common patterns
    loc["effect_types"]["toss"] = loc["effect_types"].get("knockup", "Knockup")
    
    # Core stat keywords for effect categorization
    common_stats = {
        "cooldown": "Cooldown",
        "duration": "Duration",
        "range": "Range",
        "radius": "Radius",
        "charges": "Charges",
        "delay": "Delay",
        "speed": "Speed",
        "damage": "Damage",
        "resist": "Resist",
        "armor": "Armor",
        "regen": "Regen",
        "lifesteal": "Lifesteal",
        "amp": "Amp",
        "bash": "Bash",
        "movement": "Movement",
        "weapon": "Weapon",
        "spirit": "Spirit",
        "stamina": "Stamina"
    }
    for k, v in common_stats.items():
        if k not in loc["effect_types"]:
            loc["effect_types"][k] = v

    return loc
