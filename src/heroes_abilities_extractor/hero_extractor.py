import sys
from pathlib import Path

# Add src to path if needed (though pipeline should handle it)
from mapping_handler import MAPPING

# Rename maps from the prototype `convert_hero.py`

# Logic for renames is now centralized in mapping_handler.MAPPING

VALUE_TYPE_RENAME = {
    "MODIFIER_VALUE_BASEATTACK_DAMAGE_PERCENT": "attack_damage_pct",
    "MODIFIER_VALUE_BASE_HEALTH_PERCENT":       "health_pct",
    "MODIFIER_VALUE_TECH_POWER":                "spirit_power",
}


def _extract_purchase_bonuses(raw_bonuses: dict) -> dict:
    """Restructure purchase bonuses by slot and net_worth milestone."""
    result = {}
    
    # Map the internal slot directly to the standard RAG property key
    SLOT_TO_TYPE = {
        "EItemSlotType_WeaponMod": "weapon_damage_pct",
        "EItemSlotType_Armor": "max_health",
        "EItemSlotType_Tech": "spirit_power"
    }

    for slot_key, items in raw_bonuses.items():
        slot_name = MAPPING.get_slot_name(slot_key)
        stat_type = MAPPING.get_stat_name(slot_key)
        
        milestones = []
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    gold = item.get("nGoldThreshold", 0)
                    val = item.get("flBonus", 0)
                    milestones.append({
                        "net_worth": gold,
                        "value": val,
                        "type": stat_type
                    })
        result[slot_name] = milestones
    return result


def _extract_good_items(raw_bucketing: dict) -> list[str]:
    """Filter items draft bucketing for 'Good' bucket."""
    good_items = []
    for item_key, item_data in raw_bucketing.items():
        if isinstance(item_data, dict):
            bucket = item_data.get("m_strBucket")
            if bucket == "Good":
                good_items.append(item_key)
    return good_items


def extract_shop_data(parsed_vdata: dict) -> dict:
    """Extract global shop mechanics like purchase bonuses from hero_base."""
    hero_base = parsed_vdata.get("hero_base", {})
    raw_bonuses = hero_base.get("m_MapModCostBonuses", {})
    return {
        "purchase_bonuses": _extract_purchase_bonuses(raw_bonuses)
    }


def extract_heroes(parsed_vdata: dict) -> dict:
    """Extract and normalize all hero profiles with inheritance."""
    hero_base = parsed_vdata.get("hero_base", {})
    base_m_mapStartingStats = hero_base.get("m_mapStartingStats", {})
    base_m_mapStandardLevelUpUpgrades = hero_base.get("m_mapStandardLevelUpUpgrades", {})

    processed = {}

    for key, data in parsed_vdata.items():
        if not key.startswith("hero_") or key == "hero_base":
            continue
        if not isinstance(data, dict):
            continue

        # Skip disabled or unselectable
        is_disabled = data.get("m_bDisabled", False)
        if isinstance(is_disabled, str) and is_disabled.lower() == "true":
            is_disabled = True
        
        is_selectable = data.get("m_bPlayerSelectable", False)
        if isinstance(is_selectable, str) and is_selectable.lower() == "false":
            is_selectable = False
        
        if is_disabled or not is_selectable:
             continue

        hero = {
            "hero_name": key,
            "hero_id": data.get("m_HeroID", 0),
            "hero_type": data.get("m_eHeroType", "Unknown"),
            "complexity": data.get("m_nComplexity", 1)
        }

        # 1. Base Stats (with inheritance)
        raw_stats = data.get("m_mapStartingStats", {})
        merged_stats = dict(base_m_mapStartingStats)
        merged_stats.update(raw_stats)
        
        hero["base_stats"] = {
            MAPPING.get_stat_name(k): v 
            for k, v in merged_stats.items()
        }

        # 2. Level Upgrades (with inheritance)
        raw_level_up = data.get("m_mapStandardLevelUpUpgrades", {})
        merged_lvl = dict(base_m_mapStandardLevelUpUpgrades)
        merged_lvl.update(raw_level_up)
        
        hero["level_upgrades"] = {
            MAPPING.get_stat_name(k): v
            for k, v in merged_lvl.items()
        }

        # 3. Signature Abilities
        bound_abs = data.get("m_mapBoundAbilities", {})
        signatures = {}
        for slot, aname in bound_abs.items():
            if slot.startswith("ESlot_Signature_"):
                signatures[slot] = aname
        hero["signature_abilities"] = signatures

        # 4. Purchase Bonuses (moved to shop.json) 

        # 5. Good Items
        raw_draft = data.get("m_mapItemDraftBucketing", {})
        hero["good_items"] = _extract_good_items(raw_draft)

        processed[key] = hero

    return processed
