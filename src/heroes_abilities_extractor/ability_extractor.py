import logging
from mapping_handler import MAPPING
from utils import normalize, clean_description, get_stat_name
from localization import resolve_ability_name

logger = logging.getLogger(__name__)

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

TYPE_ALIASES = {
    "spirit":         "spirit_damage",
    "weapon":         "weapon_damage",
    "toss":           "knockup",
    "tethered":       "tether",
    "combat_barrier": "shield",
    "amp":            "damage_amp",
    "custom_debuff":  "debuff",
}

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
    "fuse", "released", "velocity", "drag", "offset",
    "limit", "angle", "trail"
}

def extract_abilities(bound_abs: dict, parsed_abilities: dict, loc: dict):
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
            
            property_snake = get_stat_name(pk, loc["stat_labels"])
            eff["type"] = detected_type or property_snake or "unknown"

            loc_lower = eff.get("localized_name", "").lower()
            scale_stat = eff.get("scales_with", {}).get("stat", "")
            
            is_mechanic = any(kw in loc_lower for kw in MECHANIC_NAME_BLACKLIST) or \
                          any(kw in property_snake for kw in MECHANIC_NAME_BLACKLIST)

            is_cooldown_mechanic = eff["type"] == "unknown" and scale_stat in ("ability_cooldown", "cooldown", "level_up_boons")
            
            if eff["type"] in STAT_TYPES or is_mechanic or is_cooldown_mechanic:
                stat_key = property_snake
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
        
    return hero_abilities
