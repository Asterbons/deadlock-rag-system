"""
Shop Builder — Extracts item data from abilities.vdata, merges with localization
strings from citadel_mods_english.txt, and builds a unified shop.json.

Handles:
  - Localization parsing (display names from comments, descriptions from _desc keys)
  - HTML tag stripping for RAG-friendly text
  - Item filtering (EAbilityType_Item, non-disabled, valid tier/slot)
  - Stat normalization with clean key mapping
  - Synergy extraction (provides / scales_with)
  - Proc & effect extraction (trigger, cooldowns, effects with scaling)
  - Upgrade extraction (from m_vecAbilityUpgrades)
"""

from __future__ import annotations

import re
import logging
from pathlib import Path

from mapping_handler import MAPPING

logger = logging.getLogger(__name__)

# ── Normalization tables ────────────────────────────────────────────────────

SLOT_RENAME = {
    "EItemSlotType_WeaponMod": MAPPING.get_slot_name("EItemSlotType_WeaponMod"),
    "EItemSlotType_Armor":     MAPPING.get_slot_name("EItemSlotType_Armor"),
    "EItemSlotType_Tech":      MAPPING.get_slot_name("EItemSlotType_Tech"),
}

# m_eProvidedPropertyType → clean name
PROVIDED_PROPERTY_RENAME = {
    "MODIFIER_VALUE_TECH_POWER":                     "spirit_power",
    "MODIFIER_VALUE_WEAPON_POWER":                    "weapon_power",
    "MODIFIER_VALUE_HEALTH_MAX":                      "max_health",
    "MODIFIER_VALUE_BASEATTACK_DAMAGE_PERCENT":       "weapon_damage_pct",
    "MODIFIER_VALUE_FIRE_RATE":                       "fire_rate",
    "MODIFIER_VALUE_TECH_ARMOR_DAMAGE_RESIST":        "spirit_resistance",
    "MODIFIER_VALUE_BULLET_ARMOR_DAMAGE_RESIST":      "bullet_resistance",
    "MODIFIER_VALUE_COOLDOWN_REDUCTION_PERCENTAGE":    "cooldown_reduction",
    "MODIFIER_VALUE_TECH_RANGE_PERCENT":              "spirit_range",
    "MODIFIER_VALUE_TECH_RADIUS_PERCENT":             "spirit_radius",
    "MODIFIER_VALUE_MOVEMENT_SPEED_MAX":              "move_speed",
    "MODIFIER_VALUE_SPRINT_SPEED_BONUS":              "sprint_speed",
    "MODIFIER_VALUE_HEAL_AMP_REGEN_PERCENT":          "heal_amp",
    "MODIFIER_VALUE_HEAL_AMP_RECEIVE_PERCENT":        "heal_amp_receive",
    "MODIFIER_VALUE_AMMO_CLIP_SIZE_PERCENT":          "clip_size_pct",
    "MODIFIER_VALUE_AMMO_CLIP_SIZE":                  "clip_size",
    "MODIFIER_VALUE_TECH_LIFESTEAL":                  "spirit_lifesteal",
    "MODIFIER_VALUE_BULLET_LIFESTEAL":                "bullet_lifesteal",
    "MODIFIER_VALUE_STATUS_RESISTANCE":               "status_resistance",
    "MODIFIER_VALUE_BONUS_ABILITY_DURATION_PERCENTAGE": "ability_duration_pct",
    "MODIFIER_VALUE_BONUS_ABILITY_CHARGES":            "bonus_charges",
    "MODIFIER_VALUE_ITEM_COOLDOWN_REDUCTION_PERCENTAGE": "item_cooldown_reduction",
    "MODIFIER_VALUE_MOVEMENT_SPEED_SLOW_PERCENT":     "move_slow_pct",
    "MODIFIER_VALUE_MOVEMENT_GROUND_DASH_REDUCTION_PERCENT": "dash_reduction_pct",
    "MODIFIER_VALUE_BARRIER_HEALTH":                  "barrier_health",
    "MODIFIER_VALUE_BASE_MELEE_DAMAGE_PERCENT":       "melee_damage_pct",
    "MODIFIER_VALUE_MELEE_DAMAGE_REDUCTION_PERCENT":  "melee_damage_reduction_pct",
    "MODIFIER_VALUE_BONUS_BULLET_SPEED_PERCENT":      "bullet_speed_pct",
    "MODIFIER_VALUE_STAMINA_REGEN_PER_SECOND_PERCENTAGE": "stamina_regen_pct",
    "MODIFIER_VALUE_HEALTH_REGEN_PER_SECOND":         "health_regen",
    "MODIFIER_VALUE_OUT_OF_COMBAT_HEALTH_REGEN":      "out_of_combat_health_regen",
    "MODIFIER_VALUE_DAMAGE_PERCENT":                  "damage_pct",
    "MODIFIER_VALUE_STAMINA":                         "stamina",
    "MODIFIER_VALUE_MOVEMENT_SLOW_RESISTANCE":        "slow_resistance",
    "MODIFIER_VALUE_FIRE_RATE_SLOW":                  "fire_rate_slow",
    "MODIFIER_VALUE_RELOAD_SPEED":                    "reload_speed",
    "MODIFIER_VALUE_TECH_DAMAGE_PERCENT":             "spirit_damage_pct",
    "MODIFIER_VALUE_HEAL_AMP_CAST_PERCENT":           "heal_amp_cast",
    "MODIFIER_VALUE_HEAL_DEGEN_RESISTANCE":           "heal_degen_resistance",
    "MODIFIER_VALUE_TECH_ARMOR_DAMAGE_RESIST_REDUCTION": "spirit_resistance_reduction",
    "MODIFIER_VALUE_BULLET_ARMOR_DAMAGE_RESIST_REDUCTION": "bullet_resistance_reduction",
    "MODIFIER_VALUE_RESPAWN_TIME_PERCENTAGE":          "respawn_time_pct",
    "MODIFIER_VALUE_HEALTH_MAX_PERCENT":              "max_health_pct",
    "MODIFIER_VALUE_TECH_POWER_PERCENT":              "spirit_power_pct",
    "MODIFIER_VALUE_BASE_HEALTH_PERCENT":             "base_health_pct",
}

# Scale type → clean name
SCALE_TYPE_RENAME = {
    "EItemCooldown":    "item_cooldown_reduction",
    "ETechCooldown":    "spirit_cooldown",
    "ETechPower":       "spirit_power",
    "ETechDuration":    "spirit_duration",
    "ETechRange":       "spirit_range",
    "EChannelDuration": "channel_duration",
    "EHealingOutput":   "healing_output",
    "EBuildUpRate":     "buildup_rate",
    "ELevelUpBoons":    "level_up_boons",
}

# Property name → clean stat name (for stats dict and upgrade keys)
PROPERTY_RENAME = {
    "TechResist":             "spirit_resistance",
    "BulletResist":           "bullet_resistance",
    "TechPower":              "spirit_power",
    "WeaponPower":            "weapon_power",
    "SpiritPower":            "spirit_power",
    "AbilityCooldown":        "cooldown",
    "AbilityDuration":        "duration",
    "AbilityCastRange":       "cast_range",
    "AbilityCharges":         "charges",
    "AbilityCastDelay":       "cast_delay",
    "ProcBonusMagicDamage":   "proc_spirit_damage",
    "HeadShotBonusDamage":    "headshot_damage",
    "BonusHealth":            "max_health",
    "BaseAttackDamagePercent": "weapon_damage_pct",
    "DotHealthPercent":       "dot_health_pct",
    "DotDuration":            "dot_duration",
    "SlowPercent":            "slow_pct",
    "SlowDuration":           "slow_duration",
    "HealAmpReceivePenaltyPercent": "heal_reduction_receive_pct",
    "HealAmpRegenPenaltyPercent":   "heal_reduction_regen_pct",
    "TotalHealthRegen":       "total_heal",
    "AuraRadius":             "aura_radius",
    "TechRangeMultiplier":    "spirit_range_pct",
    "TechRadiusMultiplier":   "spirit_radius_pct",
    "ProcChance":             "proc_chance_pct",
    "ProcCooldown":           "proc_cooldown",
    "BuildUpPerShot":         "buildup_per_shot",
    "BuildUpDuration":        "buildup_duration",
    "GroundDashReductionPercent": "dash_reduction_pct",
    "BonusSprintSpeed":       "sprint_speed",
    "CasterBuffDuration":     "buff_duration",
    "TickRate":               "tick_rate",
}

# Scale function _class → effect type hint
SCALE_CLASS_TO_EFFECT_TYPE = {
    "scale_function_tech_damage":   "spirit_damage",
    "scale_function_tech_duration": "duration",
    "scale_function_tech_range":    "range",
}

# Default properties that are inherited by all items with value=0 — skip these
_INHERITED_ZERO_PROPS = frozenset({
    "AbilityDuration", "AbilityCastRange", "AbilityUnitTargetLimit",
    "AbilityCastDelay", "AbilityChannelTime", "AbilityPostCastDuration",
    "AbilityCharges", "AbilityCooldownBetweenCharge", "ChannelMoveSpeed",
    "AbilityResourceCost",
})

# HTML tag pattern for stripping
_HTML_RE = re.compile(r'<[^>]+>')
# Template placeholder pattern
_TEMPLATE_RE = re.compile(r'\{[sgf]:[^}]+\}')


# ── Localization parser ─────────────────────────────────────────────────────

def _strip_html(text: str) -> str:
    """Remove HTML tags and template placeholders from localization text."""
    text = _HTML_RE.sub("", text)
    text = _TEMPLATE_RE.sub("", text)
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def parse_localization(mods_filepath: str | Path, names_filepath: str | Path = None) -> dict:
    """Parse localization files and return display_names + descriptions.

    Display names are extracted from comment lines like:
        //Ammo Scavenger
    which precede a key like:
        "upgrade_ammo_scavenger_desc"  "..."

    Some comments use formats like:
        // "upgrade_name"  "Display Name"
        // Name - upgrade_id
    """
    text = Path(mods_filepath).read_text(encoding="utf-8")
    lines = text.splitlines()

    display_names: dict[str, str] = {}
    descriptions: dict[str, str] = {}

    # 1. Load explicit display names if names_filepath is provided
    if names_filepath:
        names_text = Path(names_filepath).read_text(encoding="utf-8")
        for line in names_text.splitlines():
            stripped = line.strip()
            match = re.match(r'\s*"([^"]+)"\s+"(.*)"', stripped)
            if not match:
                match = re.match(r'\s*"([^"]+)"\s*(.*)', stripped)
                if match and match.group(2).startswith('"'):
                    val = match.group(2).strip()
                    if val.startswith('"') and val.endswith('"'):
                        match = re.match(r'\s*"([^"]+)"\s+"(.*)"', stripped)
            
            if match:
                key = match.group(1)
                value = match.group(2)
                if not key.endswith("_search"):
                    display_names[key] = value

    last_comment_name = None

    for line in lines:
        stripped = line.strip()

        # Track comment lines for display name extraction
        if stripped.startswith("//"):
            comment_body = stripped.lstrip("/").strip()
            if not comment_body or comment_body.startswith("-"):
                last_comment_name = None
                continue

            # Format: // "upgrade_id"   "Display Name"
            # or:     // "upgrade_id"   // Display Name
            if comment_body.startswith('"'):
                parts = re.findall(r'"([^"]*)"', comment_body)
                if len(parts) >= 2:
                    # parts[0] is upgrade_id, parts[1] is display name
                    upgrade_id = parts[0]
                    display_name = parts[1]
                    display_names[upgrade_id] = display_name
                    last_comment_name = display_name
                elif len(parts) == 1:
                    # Just a commented-out key
                    last_comment_name = None
                else:
                    last_comment_name = None
                continue

            # Format: // Name - upgrade_id
            # or just: //Name
            if " - " in comment_body:
                name_part = comment_body.split(" - ")[0].strip()
                last_comment_name = name_part
            else:
                # Simple comment like "//Ammo Scavenger"
                last_comment_name = comment_body
            continue

        # Parse key-value pairs
        # Format: "key"   "value"
        match = re.match(r'\s*"([^"]+)"\s+"(.*)"', stripped)
        if not match:
            # Try tab-separated
            match = re.match(r'\s*"([^"]+)"\s*(.*)', stripped)
            if match and match.group(2).startswith('"'):
                val = match.group(2).strip()
                if val.startswith('"') and val.endswith('"'):
                    match = re.match(r'\s*"([^"]+)"\s+"(.*)"', stripped)

        if not match:
            continue

        key = match.group(1)
        value = match.group(2)

        # Description keys end with _desc
        if key.endswith("_desc"):
            base_id = key[:-5]  # Strip _desc suffix
            descriptions[base_id] = _strip_html(value)

            # Associate last comment as display name for this item
            if last_comment_name and base_id not in display_names:
                display_names[base_id] = last_comment_name
            
            # Reset comment tracker so it doesn't leak to the next item
            last_comment_name = None

        # Reset comment tracker for non-desc keys (they're property labels etc.)
        # but only if this isn't a desc line that already consumed it
        if not key.endswith("_desc"):
            # Keep comment name alive across label/postfix lines
            pass

    return {"display_names": display_names, "descriptions": descriptions}


# ── Value helpers ───────────────────────────────────────────────────────────

def _parse_numeric(val) -> float | int | None:
    """Try to parse a value as a number, stripping unit suffixes like 'm'."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return val
    s = str(val).strip().rstrip("m%s")
    try:
        f = float(s)
        i = int(f)
        return i if f == i else round(f, 6)
    except (ValueError, OverflowError):
        return None


def _normalize_provided_property(ppt: str) -> str:
    """Normalize a MODIFIER_VALUE_* string to a clean key."""
    return MAPPING.get_stat_name(ppt)


def _normalize_scale_type(st: str) -> str:
    """Normalize a scale type string to a clean key."""
    return MAPPING.get_scale_type(st)


def _normalize_property_name(name: str) -> str:
    """Normalize an internal property name to a clean key."""
    return MAPPING.get_stat_name(name)


def _tier_to_int(tier_str: str) -> int | None:
    """Convert 'EModTier_4' → 4."""
    if not tier_str or not isinstance(tier_str, str):
        return None
    match = re.search(r'(\d+)', tier_str)
    return int(match.group(1)) if match else None


# ── Proc & effect extraction ────────────────────────────────────────────────

def _detect_trigger(props: dict, activation: str) -> str | None:
    """Determine the proc trigger type based on item properties."""
    prop_names = set(props.keys())

    # Headshot-specific items
    headshot_props = {"HeadShotBonusDamage", "HealPercentPerHeadshot",
                      "BaseHealOnHeadshot"}
    if prop_names & headshot_props:
        return "on_headshot"

    # On-hit procs (bullet procs)
    on_hit_props = {"ProcBonusMagicDamage", "ProcChance", "BuildUpPerShot",
                    "DotHealthPercent"}
    if prop_names & on_hit_props:
        return "on_hit"

    # Aura items
    if "AuraRadius" in prop_names:
        return "aura"

    # Active cast items
    if activation in ("CITADEL_ABILITY_ACTIVATION_INSTANT_CAST",
                      "CITADEL_ABILITY_ACTIVATION_PRESS"):
        return "on_cast"

    # Passive with no specific trigger
    if activation == "CITADEL_ABILITY_ACTIVATION_PASSIVE":
        return "passive"

    return None


def _extract_proc(props: dict, activation: str) -> dict | None:
    """Extract proc/effect data from item properties."""
    trigger = _detect_trigger(props, activation)
    if trigger is None:
        return None

    proc: dict = {"trigger": trigger}

    # Cooldowns
    cd_prop = props.get("AbilityCooldown", {})
    if isinstance(cd_prop, dict):
        cd_val = _parse_numeric(cd_prop.get("m_strValue"))
        if cd_val and cd_val > 0:
            proc["item_cooldown_sec"] = cd_val

    proc_cd_prop = props.get("ProcCooldown", {})
    if isinstance(proc_cd_prop, dict):
        proc_cd_val = _parse_numeric(proc_cd_prop.get("m_strValue"))
        if proc_cd_val and proc_cd_val > 0:
            proc["proc_cooldown_sec"] = proc_cd_val

    # Proc chance
    chance_prop = props.get("ProcChance", {})
    if isinstance(chance_prop, dict):
        chance = _parse_numeric(chance_prop.get("m_strValue"))
        if chance is not None:
            proc["proc_chance_pct"] = chance

    # Effects
    effects = []
    for prop_name, prop_data in props.items():
        if not isinstance(prop_data, dict):
            continue
        val = _parse_numeric(prop_data.get("m_strValue"))
        if val is None or val == 0:
            continue

        sf = prop_data.get("m_subclassScaleFunction", {})
        if not isinstance(sf, dict):
            sf = {}

        scale_class = sf.get("_class", "")
        scale_stat_type = sf.get("m_eSpecificStatScaleType", "")

        # Only extract effects for properties that scale with damage/power
        if scale_class in SCALE_CLASS_TO_EFFECT_TYPE:
            effect_type = SCALE_CLASS_TO_EFFECT_TYPE[scale_class]
            scale_stat = _normalize_scale_type(scale_stat_type) if scale_stat_type else None

            # Try to find a ratio — not always explicit in vdata
            ratio = None
            scale_factor = sf.get("m_flStatScale")
            if scale_factor is not None:
                ratio = _parse_numeric(scale_factor)

            if ratio is None and scale_stat is not None:
                logger.warning(
                    "Item prop '%s': scaling with '%s' but no explicit ratio found, "
                    "setting ratio=null", prop_name, scale_stat
                )

            # Build description
            if scale_stat and ratio is not None:
                desc = f"{val} + ({scale_stat} * {ratio})"
            elif scale_stat:
                desc = f"{val} (scales with {scale_stat})"
            else:
                desc = str(val)

            effects.append({
                "type": effect_type,
                "property": _normalize_property_name(prop_name),
                "base_value": val,
                "scales_with": {
                    "stat": scale_stat,
                    "ratio": ratio,
                } if scale_stat else None,
                "description": desc,
            })

    if effects:
        proc["effects"] = effects

    return proc if (effects or proc.get("item_cooldown_sec") or trigger == "on_cast") else None


# ── Synergy extraction ──────────────────────────────────────────────────────

def _extract_synergies(props: dict) -> dict:
    """Extract provides/scales_with synergy tags from properties."""
    provides: list[str] = []
    scales_with: list[str] = []

    for prop_name, prop_data in props.items():
        if not isinstance(prop_data, dict):
            continue

        val = _parse_numeric(prop_data.get("m_strValue"))

        # Provides: check m_eProvidedPropertyType
        ppt = prop_data.get("m_eProvidedPropertyType", "")
        if ppt and ppt != "MODIFIER_VALUE_INVALID":
            # Skip universal inherited zero-value entries
            if prop_name in ("TechPower", "WeaponPower") and (val is None or val == 0):
                continue
            clean = _normalize_provided_property(ppt)
            if clean not in provides:
                provides.append(clean)

        # Scales_with: check m_subclassScaleFunction
        sf = prop_data.get("m_subclassScaleFunction", {})
        if isinstance(sf, dict):
            sst = sf.get("m_eSpecificStatScaleType", "")
            if sst and (val is not None and val != 0
                        and prop_name not in _INHERITED_ZERO_PROPS):
                clean_s = _normalize_scale_type(sst)
                if clean_s not in scales_with:
                    scales_with.append(clean_s)

            vec = sf.get("m_vecScalingStats", [])
            if isinstance(vec, list) and (val is not None and val != 0
                                           and prop_name not in _INHERITED_ZERO_PROPS):
                for s in vec:
                    clean_v = _normalize_scale_type(s)
                    if clean_v not in scales_with:
                        scales_with.append(clean_v)

    return {"provides": provides, "scales_with": scales_with}


# ── Upgrade extraction ──────────────────────────────────────────────────────

def _extract_upgrades(item_data: dict) -> dict | None:
    """Extract upgrade bonuses from m_vecAbilityUpgrades."""
    raw = item_data.get("m_vecAbilityUpgrades")
    if not raw:
        return None

    # Can be a single dict or a list of dicts
    if isinstance(raw, dict):
        upgrade_list = [raw]
    elif isinstance(raw, list):
        upgrade_list = raw
    else:
        return None

    result: dict = {}
    for upgrade_block in upgrade_list:
        if not isinstance(upgrade_block, dict):
            continue
        prop_upgrades = upgrade_block.get("m_vecPropertyUpgrades", [])
        if not isinstance(prop_upgrades, list):
            continue

        for pu in prop_upgrades:
            if not isinstance(pu, dict):
                continue
            prop_name = pu.get("m_strPropertyName", "")
            bonus = _parse_numeric(pu.get("m_strBonus"))
            if prop_name and bonus is not None:
                clean_name = _normalize_property_name(prop_name) + "_bonus"
                result[clean_name] = bonus

    return result if result else None


# ── Stats extraction ────────────────────────────────────────────────────────

def _extract_stats(props: dict) -> dict:
    """Extract base stat values from properties that provide modifiers."""
    stats: dict = {}

    for prop_name, prop_data in props.items():
        if not isinstance(prop_data, dict):
            continue

        ppt = prop_data.get("m_eProvidedPropertyType", "")
        if not ppt or ppt == "MODIFIER_VALUE_INVALID":
            continue

        val = _parse_numeric(prop_data.get("m_strValue"))
        if val is None or val == 0:
            continue

        # Skip universal inherited zero-value entries
        if prop_name in ("TechPower", "WeaponPower") and val == 0:
            continue

        clean_name = _normalize_property_name(prop_name)
        stats[clean_name] = val

    return stats


# ── Main extraction ─────────────────────────────────────────────────────────

def extract_items(parsed_abilities: dict, localization: dict) -> list[dict]:
    """Extract all valid shop items from parsed abilities.vdata.

    Args:
        parsed_abilities: Full parsed dict from abilities.vdata
        localization: Result of parse_localization()

    Returns:
        List of item dicts with the full schema
    """
    display_names = localization.get("display_names", {})
    descriptions = localization.get("descriptions", {})

    items: list[dict] = []
    skipped = 0

    for item_id, item_data in parsed_abilities.items():
        if not isinstance(item_data, dict):
            continue
        if item_data.get("m_eAbilityType") != "EAbilityType_Item":
            continue
        if item_data.get("m_bDisabled", False):
            skipped += 1
            continue
        
        # Skip template/base items (e.g. weapon_upgrade_t1)
        if re.match(r'.+_upgrade_t[1-5]$', item_id):
            skipped += 1
            continue

        tier_str = item_data.get("m_iItemTier", "")
        slot_str = item_data.get("m_eItemSlotType", "")

        tier = _tier_to_int(tier_str)
        slot = SLOT_RENAME.get(slot_str)

        if tier is None or slot is None:
            skipped += 1
            continue

        activation = item_data.get("m_eAbilityActivation", "")
        passive = activation == "CITADEL_ABILITY_ACTIVATION_PASSIVE"

        props = item_data.get("m_mapAbilityProperties", {})

        # Lookup display name and description
        name = display_names.get(item_id)
        if not name:
            # Fallback formatting: upgrade_clip_size -> Clip Size
            clean = item_id.replace("upgrade_", "").replace("weapon_", "").replace("armor_", "").replace("tech_", "")
            name = " ".join(word.capitalize() for word in clean.split("_"))
        description = descriptions.get(item_id, "")

        # Build item record
        item: dict = {
            "id": item_id,
            "name": name,
            "tier": tier,
            "slot": slot,
            "passive": passive,
            "upgrades_from": item_data.get("m_vecComponentItems", []),
            "upgrades_into": None,
        }

        # Description
        if description:
            item["description"] = description

        # Stats
        stats = _extract_stats(props)
        if stats:
            item["stats"] = stats

        # Proc / Effects
        proc = _extract_proc(props, activation)
        if proc:
            item["proc"] = proc

        # (Legacy upgrade extraction removed because items don't use AP leveling)

        # Synergies
        synergies = _extract_synergies(props)
        if synergies["provides"] or synergies["scales_with"]:
            item["synergies"] = synergies

        items.append(item)

    logger.info("Extracted %d items, skipped %d", len(items), skipped)
    return items


# ── Shop JSON assembly ──────────────────────────────────────────────────────

def build_shop_json(items: list[dict], purchase_bonuses: dict) -> dict:
    """Build the final shop.json structure.

    Args:
        items: List of extracted item dicts
        purchase_bonuses: Global purchase bonuses from hero_extractor

    Returns:
        Complete shop.json dict
    """
    # Rename purchase_bonuses keys: tech → spirit
    renamed_bonuses = {}
    for k, v in purchase_bonuses.items():
        if k == "tech":
            renamed_bonuses["spirit"] = v
        else:
            renamed_bonuses[k] = v

    # Rename weapon_mod → weapon
    if "weapon_mod" in renamed_bonuses:
        renamed_bonuses["weapon"] = renamed_bonuses.pop("weapon_mod")

    def _replace_tech_with_spirit(obj):
        if isinstance(obj, dict):
            return {
                (k.replace("tech", "spirit") if "tech" in k else k): 
                _replace_tech_with_spirit(v)
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [_replace_tech_with_spirit(v) for v in obj]
        elif isinstance(obj, str):
            return obj.replace("tech", "spirit") if "tech" in obj else obj
        return obj

    renamed_bonuses = _replace_tech_with_spirit(renamed_bonuses)
    items = _replace_tech_with_spirit(items)

    # 1. build index
    item_by_id = {item["id"]: item for item in items}

    # 2. fill upgrades_into
    for item in items:
        for component_id in item.get("upgrades_from", []):
            if component_id in item_by_id:
                item_by_id[component_id]["upgrades_into"] = item["id"]
            else:
                logger.warning("Component %s not found for %s", component_id, item["id"])

    shop: dict = {
        "global_mechanics": {
            "purchase_bonuses": renamed_bonuses,
        },
        "weapon": [],
        "vitality": [],
        "spirit": [],
    }

    for item in items:
        slot = item.get("slot", "")
        if slot in shop:
            shop[slot].append(item)

    # Sort items within each slot by tier
    for slot_key in ("weapon", "vitality", "spirit"):
        shop[slot_key].sort(key=lambda x: x.get("tier", 0))

    return shop
