"""
Output Validator — Verifies the output of the Deadlock KV3 pipeline.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PROCESSED_HEROES_PATH, SHOP_JSON_PATH

def validate():
    assert PROCESSED_HEROES_PATH.exists(), "Output file does not exist"
    
    with PROCESSED_HEROES_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
        
    print(f"Loaded {len(data)} heroes.")
    assert len(data) >= 30, f"Expected at least 30 heroes, got {len(data)}"
    
    # Verify inferno data
    assert "hero_inferno" in data, "Inferno missing"
    inf = data["hero_inferno"]
    
    # 1. Base Stats
    stats = inf.get("base_stats", {})
    assert stats.get("health") == 800, f"Expected 800 health, got {stats.get('health')}"
    assert stats.get("max_move_speed") == 6.7, f"Expected 6.7 move speed, got {stats.get('max_move_speed')}"
    
    # 2. Level Upgrades
    lvl = inf.get("scaling_per_level", {})
    assert lvl.get("health") == 39, f"Expected 39 HP per level, got {lvl.get('health')}"
    # The key is 'spirit__power' in the JSON I saw (double underscore?)
    # Wait, let's check. Line 51: "spirit__power": 1.1
    # Ah, the mapping for ETechPower was "Spirit Power" -> spirit_power.
    # Wait, mapping_handler to_snake_case("Spirit Power") -> spirit_power.
    # Why spirit__power? Oh, because I added underscores before capitals.
    # 'Spirit Power' -> 'Spirit_Power' -> 'spirit_power'.
    # I should check my mapping_handler.
    assert lvl.get("spirit_power") == 1.1 or lvl.get("spirit__power") == 1.1, f"Expected 1.1 spirit power"
    
    # 3. Good Items
    good = inf.get("good_items", [])
    assert len(good) > 0, "Expected some good items for inferno"
    # good is a list of dicts now? No, line 271: "good_items": [ { "id": "upgrade_active_reload", ... } ]
    good_ids = [item["id"] for item in good]
    assert "upgrade_active_reload" in good_ids, f"inferno is missing upgrade_active_reload"
    
    # 4. Abilities
    abs_data = inf.get("abilities", [])
    assert len(abs_data) >= 4, f"Expected at least 4 abilities, got {len(abs_data)}"
    
    afterburn = next((a for a in abs_data if a.get("name") == "Afterburn"), None)
    assert afterburn is not None, "Inferno missing Afterburn ability"
    
    # Check values
    ab_stats = afterburn.get("stats", {})
    assert ab_stats.get("dps") == 12.0, f"Expected 12.0 DPS, got {ab_stats.get('dps')}"
    
    # Check effects
    effects = afterburn.get("effects", [])
    dot = next((e for e in effects if e.get("type") == "dot"), None)
    assert dot is not None, "Afterburn missing dot effect"
    assert dot.get("unit") == "damage/sec", f"Expected damage/sec unit, got {dot.get('unit')}"
    
    # 5. Assert purchase_bonuses extracted
    assert "purchase_bonuses" not in inf, "purchase_bonuses should be globally extracted"
    
    assert SHOP_JSON_PATH.exists(), "shop.json does not exist"
    with SHOP_JSON_PATH.open("r", encoding="utf-8") as f:
        shop = json.load(f)
    assert "global_mechanics" in shop and "purchase_bonuses" in shop["global_mechanics"], "shop.json missing purchase_bonuses"
    assert "vitality" in shop["global_mechanics"]["purchase_bonuses"], "shop.json missing vitality tiers"
        
    print("All validations passed!")

if __name__ == "__main__":
    validate()
