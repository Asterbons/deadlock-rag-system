import json
import re
import logging
import os
import sys
from pathlib import Path

def camel_to_snake(name: str) -> str:
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
    s = re.sub(r'([a-z\d])([A-Z])', r'\1_\2', s)
    return re.sub(r'_+', '_', s).lower().strip('_')

# Adjust paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from kv3_parser import parse_kv3_file
from config import (
    SHOP_JSON_PATH, HEROES_VDATA_PATH, ABILITIES_VDATA_PATH,
    HERO_NAMES_LOC_PATH, HEROES_LOC_PATH, ATTRIBUTES_LOC_PATH, MODS_LOC_PATH,
    HEROES_OUT_DIR, HEROES_INDEX_PATH
)
from mapping_handler import MAPPING


def load_shop_valid_items():
    valid = {}
    try:
        with open(SHOP_JSON_PATH, "r", encoding="utf-8") as f:
            shop = json.load(f)
            for category in ["weapon", "vitality", "spirit"]:
                for item in shop.get(category, []):
                    valid[item["id"]] = item.get("name", item["id"])
    except Exception as e:
        print(f"Error loading shop.json: {e}")
    return valid

def normalize(v):
    if v is None:
        return 0
    if isinstance(v, (int, float)):
        return int(v) if v == int(v) else round(v, 6)
    v_str = str(v).strip()
    try:
        f = float(v_str)
        return int(f) if f == int(f) else round(f, 6)
    except (ValueError, TypeError):
        return v_str

logger = logging.getLogger(__name__)

def strip_html(text: str) -> str:
    """Strip HTML tags only — used for short labels that have no inline attrs."""
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', '', text)
    clean = re.sub(r'\{g:[^}]+\}', '', clean)
    clean = clean.replace('<br>', '\n').replace('</br>', '')
    return clean.strip()

def clean_description(text: str, inline_attrs: dict) -> str:
    """Full description cleaning pipeline.

    Order:
      1. Replace {g:citadel_inline_attribute:'X'} with inline_attrs[X]
      2. Replace {s:StatName} placeholders with literal "X"
      3. Strip HTML tags: <span …>, </span>, <br>, <b>, </b>, <Panel …>
      4. Collapse multiple spaces into one
      5. Strip leading/trailing whitespace
    """
    if not text:
        return ""

    # 1. Inline attribute tags
    def _replace_inline(m):
        key = m.group(1)
        return inline_attrs.get(key, key.lower())

    clean = re.sub(
        r"\{g:citadel_inline_attribute:'([^']+)'\}",
        _replace_inline,
        text,
    )

    def _replace_binding(m):
        return f"[{m.group(1)}]"

    clean = re.sub(
        r"\{g:citadel_binding:'([^']+)'\}",
        _replace_binding,
        clean,
    )

    # Strip any remaining {g:…} tags (e.g. binding hints)
    clean = re.sub(r'\{g:[^}]+\}', '', clean)

    # 2. Stat placeholders  {s:StatName}  → "X"
    clean = re.sub(r'\{s:[^}]+\}', 'X', clean)

    # 3. Strip HTML tags
    clean = re.sub(r'<[^>]+>', '', clean)
    clean = clean.replace('<br>', ' ').replace('</br>', '')

    # 4. Collapse multiple spaces
    clean = re.sub(r'  +', ' ', clean)

    # 5. Strip leading/trailing whitespace
    return clean.strip()

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

def extract_hero_tags(internal_key, display_name, hero_tags_by_keyword):
    short_key = internal_key.replace("hero_", "").lower()
    disp_lower = display_name.lower()
    for tk, tags in hero_tags_by_keyword.items():
        if tk == short_key or tk in disp_lower:
            return tags
    return []

def get_stat_name(raw_key, stat_labels=None):
    if stat_labels and raw_key in stat_labels:
        label = stat_labels[raw_key].get("label", "")
        if label:
            # Convert "Movement Speed" to "movement_speed"
            clean = label.lower().replace(" ", "_")
            return re.sub(r'[^a-z0-9_]', '', clean)
    return MAPPING.get_stat_name(raw_key)

def infer_damage_type(hero_abilities):
    dtypes = set()
    for a in hero_abilities:
        for e in a.get("effects", []):
            if e.get("type") in ["spirit_damage", "dot"]:
                dtypes.add("spirit")
            elif e.get("type") == "bullet_damage":
                dtypes.add("bullet")
            if e.get("type") == "dot":
                dtypes.add("dot")
    return list(dtypes)

def infer_utility(hero_abilities):
    utils = set()
    for a in hero_abilities:
        for e in a.get("effects", []):
            t = e.get("type")
            if t in ["slow", "stun", "silence", "heal", "buff", "debuff"]:
                if t == "buff" or t == "debuff":
                     # might need more granular, let's keep it simple
                     pass
                else:
                     utils.add(t)
        # Also check tags if any mobility
        if a.get("targeting") == "self" and ("dash" in a.get("name", "").lower() or "jump" in a.get("name", "").lower()):
            utils.add("mobility")
    return list(utils)

def extract_hero_profile(h_key, h_data, base_stats_fallback, base_scaling_fallback, loc, parsed_abilities, valid_items):
    hero = {}
    hero["hero"] = h_key
    hero["hero_id"] = normalize(h_data.get("m_HeroID", 0))
    
    disp_name = loc["hero_names"].get(h_key, h_key)
    hero["name"] = disp_name
    
    hero_type = h_data.get("m_eHeroType", "Unknown")
    hero["hero_type"] = hero_type.replace("ECitadelHeroType_", "")
    hero["complexity"] = normalize(h_data.get("m_nComplexity", 1))
    
    tags = {"flavor": [], "playstyle": [], "damage_type": [], "utility": []}
    flavor = extract_hero_tags(h_key, disp_name, loc["hero_tags_by_keyword"])
    tags["flavor"] = flavor
    
    if hero["hero_type"].lower() != "unknown":
        tags["playstyle"].append(hero["hero_type"].lower())
        
    hero["tags"] = tags # update contents later
    
    # --- Base Stats ---
    raw_stats = dict(base_stats_fallback)
    raw_stats.update(h_data.get("m_mapStartingStats", {}))
    
    clean_stats = {}
    for k, v in raw_stats.items():
        val = normalize(v)
        if isinstance(val, (int, float)):
            if "Scale" in k or k in ["EHeroSpiritLifestealEffectiveness", "EHeroBulletLifestealEffectiveness"]:
                 if val == 1.0: continue
            if "AbilityResource" in k and val == 0:
                 continue
            clean_name = get_stat_name(k, loc["stat_labels"])
            if clean_name == "max_health" or clean_name == "health": clean_name = "health"
            elif clean_name == "health_regen": clean_name = "health_regen"
            clean_stats[clean_name] = val
    hero["base_stats"] = clean_stats

    # --- Scaling ---
    raw_scaling = dict(base_scaling_fallback)
    raw_scaling.update(h_data.get("m_mapStandardLevelUpUpgrades", {}))
    clean_scaling = {}
    for k, v in raw_scaling.items():
        val = normalize(v)
        if isinstance(val, (int, float)) and val != 0:
            clean_name = get_stat_name(k, loc["stat_labels"])
            if clean_name == "base_health_from_level": clean_name = "health"
            if clean_name == "tech_power": clean_name = "spirit_power"
            clean_scaling[clean_name] = val
    hero["scaling_per_level"] = clean_scaling

    # --- Abilities ---
    bound_abs = h_data.get("m_mapBoundAbilities", {})
    hero_abilities = []
    
    for i in range(1, 5):
        slot_key = f"ESlot_Signature_{i}"
        ability_id = bound_abs.get(slot_key)
        if not ability_id: continue
        
        ab_data = parsed_abilities.get(ability_id, {})
        ab = {}
        ab["id"] = ability_id
        ab["slot"] = i
        ab["name"] = resolve_ability_name(ability_id, loc["ability_names"])
        
        raw_desc_parts = []
        main_desc = loc["ability_descs"].get(ability_id, "")
        if main_desc:
            raw_desc_parts.append(main_desc)
            
        for k, v in loc["ability_descs"].items():
            if k.startswith(f"{ability_id}_") and k != ability_id:
                if v and v not in raw_desc_parts:
                    raw_desc_parts.append(v)
                    
        raw_desc = " | ".join(raw_desc_parts)
        ab["description"] = clean_description(raw_desc, loc["inline_attrs"])
        
        act = ab_data.get("m_eAbilityActivation", "Unknown")
        if act == "CITADEL_ABILITY_ACTIVATION_PASSIVE":
            ab["cast_type"] = "passive"
        elif act == "CITADEL_ABILITY_ACTIVATION_TOGGLE":
            ab["cast_type"] = "toggle"
        else:
            ab["cast_type"] = "active"
            
        target = str(ab_data.get("m_eAbilityTargetingLocation", ""))
        behavior = str(ab_data.get("m_nAbilityBehaviors", "")) 
        
        if "PROJECTILE" in target or "PROJECTILE" in behavior:
            ab["targeting"] = "projectile"
        elif "AOE" in behavior:
            ab["targeting"] = "aoe"
        elif "UNIT" in target or "TARGET" in behavior:
            ab["targeting"] = "target"
        elif "BONE" in target or "SELF" in behavior:
            ab["targeting"] = "self"
        else:
            ab["targeting"] = "instant"
            
        stats = {}
        props = ab_data.get("m_mapAbilityProperties", {})
        for pk, pv in props.items():
            if not isinstance(pv, dict): continue
            val = pv.get("m_strValue")
            if val is not None and normalize(val) != 0:
                clean_pk = get_stat_name(pk, loc["stat_labels"])
                if clean_pk == "ability_cooldown": clean_pk = "cooldown"
                elif clean_pk == "ability_cast_range": clean_pk = "cast_range"
                elif clean_pk == "ability_duration": clean_pk = "duration"
                if isinstance(val, (int, float)) and val in [0, -1, 0.0, -1.0]:
                    pass # Skip noisy stats
                else:
                    stats[clean_pk] = normalize(val)
        ab["stats"] = stats
        
        UNIT_MAP = {
            "spirit_damage": "damage",
            "bullet_damage": "damage",
            "heal": "hp",
            "dot": "damage/sec",
            "stun": "seconds",
            "slow": "%",
            "cooldown": "s",
            "duration": "s",
            "range": "m",
            "radius": "m",
            "charges": "charges",
            "delay": "s",
            "speed": "m/s",
            "move_speed": "m/s",
            "spirit_power": "spirit",
            "weapon_power": "weapon",
            "tech_power": "spirit",
            "fire_rate": "%",
            "lifesteal": "%",
            "regen": "hp/s",
            "armor": "%",
            "resist": "%",
            "spirit_resist": "%",
            "bullet_resist": "%"
        }

        effects = []
        for pk, pv in props.items():
            if not isinstance(pv, dict): continue
            sf = pv.get("m_subclassScaleFunction")
            val = normalize(pv.get("m_strValue", 0))
            lower_pk = pk.lower()

            if pk in MAPPING.effect_property_blacklist:
                continue

            # BUG 2: Distance/size values extracted as effects
            if isinstance(val, str) and val.endswith("m"):
                stat_key = get_stat_name(pk, loc["stat_labels"])
                if stat_key == "ability_cooldown": stat_key = "cooldown"
                elif stat_key == "ability_cast_range": stat_key = "cast_range"
                elif stat_key == "ability_duration": stat_key = "duration"
                ab["stats"][stat_key] = val
                continue

            # effect mapping
            effect_type = None
            localized_label = ""
            
            # Priority 1: Scale Function Class
            if sf:
                sf_class = sf.get("_class")
                if sf_class == "scale_function_tech_damage":
                    effect_type = "spirit_damage"
                elif sf_class == "scale_function_healing":
                    effect_type = "heal"
                    
            # Priority 2: m_eProvidedPropertyType label
            if effect_type is None:
                provided_type = pv.get("m_eProvidedPropertyType")
                if provided_type and provided_type in loc["stat_labels"]:
                    localized_label = loc["stat_labels"][provided_type].get("label", "")
            
            # Priority 3: Property name label
            if effect_type is None and not localized_label:
                if pk in loc["stat_labels"]:
                    localized_label = loc["stat_labels"][pk].get("label", "")
            
            # Priority 4: Search localized label for keywords
            if effect_type is None and localized_label:
                label_lower = localized_label.lower()
                for et_key, et_label in loc["effect_types"].items():
                    if et_key in label_lower or (et_label and et_label.lower() in label_lower):
                        effect_type = et_key
                        break
            
            # Priority 5: Fallback to snake_case property name
            if effect_type is None:
                property_snake = get_stat_name(pk, loc["stat_labels"])
                for et_key in loc["effect_types"]:
                    if et_key and et_key in property_snake:
                        effect_type = et_key
                        break
                        
            # Hack for telepunch / bebop toss / etc
            if effect_type is None and any(w in pk.lower() for w in ["toss", "punch", "knockback", "knockup"]):
                effect_type = "knockup"
                        
            eff = {"type": effect_type or "unknown", "base_value": val}
            if localized_label:
                eff["localized_name"] = localized_label
                if eff["type"] == "unknown":
                    # Fallback: if we have a label but no type, try to map label directly
                    lbl = localized_label.lower()
                    if "slow" in lbl: eff["type"] = "slow"
                    elif "stun" in lbl: eff["type"] = "stun"
                    elif "knockup" in lbl or "knockback" in lbl or "toss" in lbl: eff["type"] = "knockup"
                    elif "silence" in lbl: eff["type"] = "silence"
                    elif "disarm" in lbl: eff["type"] = "disarm"
                    elif "heal" in lbl or "regen" in lbl: eff["type"] = "heal"
                    elif "damage" in lbl: eff["type"] = "damage"
                    elif "cooldown" in lbl: eff["type"] = "cooldown"
                    elif "duration" in lbl: eff["type"] = "duration"
                    elif "range" in lbl: eff["type"] = "range"
                    elif "radius" in lbl: eff["type"] = "radius"
                    elif "spirit" in lbl: eff["type"] = "spirit_power"
                    elif "weapon" in lbl: eff["type"] = "weapon_power"

            if sf:
                ratio = normalize(sf.get("m_flStatScale", 1.0))
                raw_stat = sf.get("m_eSpecificStatScaleType", "spirit_power")
                stat = MAPPING.get_scale_type(raw_stat)
                
                eff["scales_with"] = {"stat": stat, "ratio": ratio}
                eff["formula"] = f"{val} + ({stat} * {ratio})"

            TYPE_ALIASES = {
                "spirit":         "spirit_damage",
                "weapon":         "weapon_damage",
                "toss":           "knockup",
                "tethered":       "tether",
                "combat_barrier": "shield",
                "amp":            "damage_amp",
                "custom_debuff":  "debuff",
            }
            detected_type = eff["type"]
            if detected_type == "damage":
                scale_stat = eff.get("scales_with", {}).get("stat", "")
                if "melee" in scale_stat:
                    detected_type = "melee_damage"
                elif "bullet" in scale_stat or "weapon" in scale_stat:
                    detected_type = "bullet_damage"
                else:
                    detected_type = "spirit_damage"
            else:
                detected_type = TYPE_ALIASES.get(detected_type, detected_type)
            eff["type"] = detected_type

            STAT_TYPES = {
                'cooldown', 'duration', 'radius', 'range',
                'speed', 'delay', 'charges', 'stamina',
                'armor', 'resist', 'regen', 'lifesteal',
            }
            MECHANIC_NAME_BLACKLIST = {
                "lifetime", "buildup", "recast", "window",
                "frequency", "generation", "summon", "count",
                "rate", "interval", "angle", "time-stop",
                "per bullet", "per headshot", "per shot",
            }
            
            loc_lower = eff.get("localized_name", "").lower()
            scale_stat = eff.get("scales_with", {}).get("stat", "")
            
            is_mechanic = any(kw in loc_lower for kw in MECHANIC_NAME_BLACKLIST)
            is_cooldown_mechanic = eff["type"] == "unknown" and scale_stat in ("ability_cooldown", "cooldown", "level_up_boons")
            
            if eff["type"] in STAT_TYPES or is_mechanic or is_cooldown_mechanic:
                stat_key = get_stat_name(pk, loc["stat_labels"])
                if stat_key == "ability_cooldown": stat_key = "cooldown"
                elif stat_key == "ability_cast_range": stat_key = "cast_range"
                elif stat_key == "ability_duration": stat_key = "duration"
                ab["stats"][stat_key] = val
                continue

            # --- Filtering rules ---
            if isinstance(val, (int, float)) and val in [0, -1, 0.0, -1.0]:
                continue
                
            has_formula = "formula" in eff
            has_scale = eff.get("scales_with", {}).get("ratio") is not None
            has_value = isinstance(val, (int, float)) and eff["type"] != "unknown"

            # SKIP if no formula, no scaling, and zero/null value
            if not has_formula and not has_scale and not has_value:
                continue

            # SKIP generic multipliers like 0.5 (50%) IF no formula/scale
            if not has_formula and not has_scale and isinstance(val, (int, float)) and 0 < abs(val) < 1:
                continue

            if eff["type"] == "unknown":
                logger.warning(f"Unknown effect type for property: {pk} (Label: {localized_label})")

            # Add unit field
            eff["unit"] = UNIT_MAP.get(eff["type"], "")
            if localized_label and "duration" in localized_label.lower():
                eff["unit"] = "s"

            if eff not in effects:
                effects.append(eff)
                
        upgrades = []
        upgs = ab_data.get("m_vecAbilityUpgrades", [])
        if isinstance(upgs, list):
            for lvl, u_data in enumerate(upgs, start=1):
                if not isinstance(u_data, dict): continue
                upg_desc_key = f"{ability_id}_t{lvl}"
                upg_desc = clean_description(
                    loc["upgrade_descs"].get(upg_desc_key, ""), loc["inline_attrs"]
                )
                
                changes = {}
                u_props = u_data.get("m_vecPropertyUpgrades", [])
                if isinstance(u_props, list):
                    for entry in u_props:
                        if not isinstance(entry, dict): continue
                        prop_name = get_stat_name(entry.get("m_strPropertyName", ""), loc["stat_labels"])
                        if prop_name == "ability_cooldown": prop_name = "cooldown"
                        bonus = normalize(entry.get("m_strBonus", entry.get("m_flBonus", 0)))
                        if isinstance(bonus, (int, float)) and bonus in [0, -1, 0.0, -1.0]:
                            continue

                        upgrade_type = entry.get("m_eUpgradeType", "EAddFlat")
                        
                        if upgrade_type == "EAddFlat" or not upgrade_type:
                            changes[prop_name] = bonus
                        elif upgrade_type == "EMultiplyScale":
                            changes[f"{prop_name}_multiplier"] = bonus
                        elif upgrade_type == "EAddToScale":
                            changes[f"{prop_name}_scale_bonus"] = bonus
                            
                if not upg_desc and not changes:
                    continue
                    
                if not upg_desc and changes:
                    parts = []
                    for k, v in changes.items():
                        name = k.replace('_', ' ').title()
                        prefix = "+" if isinstance(v, (int, float)) and v > 0 else ""
                        
                        base_k = k.replace('_multiplier', '').replace('_scale_bonus', '')
                        unit = UNIT_MAP.get(base_k, "")
                        if "duration" in k or "cooldown" in k: unit = "s"
                        elif "radius" in k or "range" in k or "distance" in k: unit = "m"
                        
                        parts.append(f"{prefix}{v}{unit} {name}")
                    upg_desc = " and ".join(parts)
                    
                upgrades.append({
                    "level": lvl,
                    "description": upg_desc,
                    "changes": changes
                })
        
        ab["effects"] = effects
        ab["upgrades"] = upgrades
        hero_abilities.append(ab)
        
    hero["abilities"] = hero_abilities

    # Playstyle inferred from effects
    tags["damage_type"].extend(infer_damage_type(hero_abilities))
    tags["utility"].extend(infer_utility(hero_abilities))
    if "Damage" in hero_type: tags["damage_type"].append("burst") # generic
    
    # Remove duplicates from tags
    for tk in tags: tags[tk] = list(set(tags[tk]))
    hero["tags"] = tags

    # --- Weapon ---
    weapon_id = bound_abs.get("ESlot_Weapon_Primary", "")
    weapon_data = parsed_abilities.get(weapon_id, {})
    weapon_props = weapon_data.get("m_WeaponInfo", {})
    
    weapon = {"id": weapon_id}
    if weapon_props:
        weapon["bullet_damage"] = normalize(weapon_props.get("m_flBulletDamage", 0))
        cycle = normalize(weapon_props.get("m_flCycleTime", 0))
        weapon["rounds_per_sec"] = normalize(round(1.0 / cycle, 2)) if cycle else 0
        weapon["clip_size"] = normalize(weapon_props.get("m_iClipSize", 0))
        weapon["reload_time"] = normalize(weapon_props.get("m_reloadDuration", 0))
        weapon["bullet_speed"] = normalize(weapon_props.get("m_flBulletSpeed", 0))
        weapon["bullets_per_shot"] = normalize(weapon_props.get("m_iBullets", 1))
        weapon["bullet_gravity"] = normalize(weapon_props.get("m_flBulletGravityScale", 0.0))
        weapon["spread"] = normalize(weapon_props.get("m_Spread", 0))
        weapon["standing_spread"] = normalize(weapon_props.get("m_StandingSpread", 0))
        weapon["inherit_shooter_velocity"] = normalize(weapon_props.get("m_flBulletInheritShooterVelocityScale", 0))
        
        falloff_start = normalize(weapon_props.get("m_flDamageFalloffStartRange", 0))
        falloff_end = normalize(weapon_props.get("m_flDamageFalloffEndRange", 0))
        weapon["falloff_range"] = [falloff_start, falloff_end]
        
        fs_start = normalize(weapon_props.get("m_flDamageFalloffStartScale", 1.0))
        fs_end = normalize(weapon_props.get("m_flDamageFalloffEndScale", 1.0))
        weapon["falloff_scale"] = [fs_start, fs_end]
        
        weapon["falloff_bias"] = normalize(weapon_props.get("m_flDamageFalloffBias", 0))
        
        crit_start = normalize(weapon_props.get("m_flCritBonusStart", 0))
        crit_end = normalize(weapon_props.get("m_flCritBonusEnd", crit_start))
        if crit_start == crit_end:
            weapon["crit_bonus"] = crit_start
        else:
            weapon["crit_bonus"] = [crit_start, crit_end]
            
        cr_start = normalize(weapon_props.get("m_flCritBonusStartRange", 0))
        cr_end = normalize(weapon_props.get("m_flCritBonusEndRange", 0))
        weapon["crit_range"] = [cr_start, cr_end]
        
        can_zoom = weapon_data.get("m_bCanZoom", "false")
        weapon["can_zoom"] = (can_zoom == "true" or can_zoom is True)
        
        attrs = []
        weapon_attrs = weapon_props.get("m_eWeaponAttributes", "")
        if isinstance(weapon_attrs, str) and weapon_attrs:
            attrs = [a.strip().replace("EWeaponAttribute_", "").lower() for a in weapon_attrs.split("|")]
        elif isinstance(weapon_attrs, list): 
            attrs = [a.replace("EWeaponAttribute_", "").lower() for a in weapon_attrs]
        
        weapon["attributes"] = [a for a in attrs if a and a != "none"]
        
    hero["weapon"] = weapon

    # --- Good Items ---
    good_items = []
    # from mapItemRecommendations or mapItemDraftBucketing
    item_recs = h_data.get("m_mapItemRecommendations", h_data.get("m_mapItemDraftBucketing", {}))
    for item_key, item_val in item_recs.items():
        if item_key not in valid_items:
            continue
        if isinstance(item_val, dict):
            if item_val.get("m_strBucket") == "Good":
                good_items.append({
                    "id": item_key,
                    "name": valid_items[item_key]
                })
    hero["good_items"] = good_items
    
    return hero

def create_index_entry(hero):
    h_idx = dict(hero)
    
    # summarize abilities
    abs_summ = []
    for ab in hero.get("abilities", []):
        summ = {
            "slot": ab["slot"],
            "name": ab["name"],
            "cast_type": ab["cast_type"],
            "targeting": ab["targeting"],
            "stats": dict(ab.get("stats", {})) # flat copy
        }
        eff_types = list(set([e.get("type", "buff") for e in ab.get("effects", [])]))
        summ["effect_types"] = eff_types
        abs_summ.append(summ)
        
    h_idx["abilities"] = abs_summ
    
    # Good items is an array of objects, simplify to just IDs for index? No, prompt says: 
    # Array of all heroes. Each entry contains everything needed. "abilities summary only".
    # Keep good_items as is.
    return h_idx

def main():
    print("Loading VDATA files...")
    heroes_data = parse_kv3_file(HEROES_VDATA_PATH)
    abilities_data = parse_kv3_file(ABILITIES_VDATA_PATH)
    
    print("Parsing localization...")
    loc = parse_localization(
        HERO_NAMES_LOC_PATH,
        HEROES_LOC_PATH,
        ATTRIBUTES_LOC_PATH,
        MODS_LOC_PATH
    )

    base_stats_fallback = heroes_data.get("hero_base", {}).get("m_mapStartingStats", {})
    base_scaling_fallback = heroes_data.get("hero_base", {}).get("m_mapStandardLevelUpUpgrades", {})

    HEROES_OUT_DIR.mkdir(parents=True, exist_ok=True)
    index_data = []

    print("Loading valid shop items...")
    valid_items = load_shop_valid_items()

    print("Extracting heroes...")
    for key, data in heroes_data.items():
        if not key.startswith("hero_") or key == "hero_base":
            continue
        if not isinstance(data, dict):
            continue
            
        def is_true(v):
            if isinstance(v, str): return v.lower() == "true"
            return bool(v)
            
        # Filter unreleased/test heroes
        if not is_true(data.get("m_bPlayerSelectable", False)): continue
        if is_true(data.get("m_bDisabled", False)): continue
        if is_true(data.get("m_bInDevelopment", False)): continue
        if is_true(data.get("m_bNeedsTesting", False)): continue
        if is_true(data.get("m_bLimitedTesting", False)): continue
        if is_true(data.get("m_bPrereleaseOnly", False)): continue

        hero = extract_hero_profile(key, data, base_stats_fallback, base_scaling_fallback, loc, abilities_data, valid_items)
        
        # Save detailed 
        hero_filename = hero["name"].lower().replace(" & ", "_and_").replace(" ", "_").replace("'", "")
        with open(HEROES_OUT_DIR / f"{hero_filename}.json", "w", encoding="utf-8") as f:
            json.dump(hero, f, indent=2, ensure_ascii=False)
            
        # Put in index
        index_data.append(create_index_entry(hero))

    # Save index
    with open(HEROES_INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)
        
    print(f"Extraction complete! Saved {len(index_data)} heroes to data/processed/heroes/ and data/processed/heroes_index.json")

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    main()
