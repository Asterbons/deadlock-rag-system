import re
from pathlib import Path

def to_snake_case(text: str) -> str:
    """Convert 'Spirit Power' -> 'spirit_power'."""
    if not text:
        return ""
    # Replace spaces and hyphens with underscores
    clean = text.replace(" ", "_").replace("-", "_")
    # Add underscores before capital letters (if not already there)
    clean = re.sub(r'(?<!^)(?=[A-Z])', '_', clean)
    return clean.lower()

class MappingHandler:
    def __init__(self, mapping_path: str | Path):
        self.mapping_path = Path(mapping_path)
        self.scale_type_map = {}
        self.stat_key_map = {}
        self.modifier_map = {}
        self.slot_map = {}
        self._parse()

    def _parse(self):
        if not self.mapping_path.exists():
            return

        current_section = None
        content = self.mapping_path.read_text(encoding="utf-8")
        
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                if "Scale Type Mapping" in line:
                    current_section = "scale"
                elif "Stat Key Mapping" in line:
                    current_section = "stat"
                elif "MODIFIER_VALUE_* Mapping" in line:
                    current_section = "modifier"
                elif "Slot Name Mapping" in line:
                    current_section = "slot"
                continue

            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()
                
                clean_val = to_snake_case(val)
                
                if current_section == "scale":
                    self.scale_type_map[key] = clean_val
                elif current_section == "stat":
                    self.stat_key_map[key] = clean_val
                elif current_section == "modifier":
                    self.modifier_map[key] = clean_val
                elif current_section == "slot":
                    self.slot_map[key] = clean_val

    def get_stat_name(self, raw_key: str) -> str:
        """Standardize a stat key using strict mapping or fallback."""
        # 1. Check strict mappings
        if raw_key in self.stat_key_map:
            return self.stat_key_map[raw_key]
        if raw_key in self.modifier_map:
            return self.modifier_map[raw_key]
        
        # 2. Fallback normalization
        clean = raw_key
        for prefix in ["MODIFIER_VALUE_", "EHero", "E", "m_fl"]:
            if clean.startswith(prefix):
                clean = clean[len(prefix):]
        if clean.startswith("Base"): clean = clean[4:]
        
        # CamelCase to snake_case
        if "_" in clean or clean.isupper():
            clean = clean.lower()
        else:
            clean = re.sub(r'(?<!^)(?=[A-Z])', '_', clean).lower()
        
        # Final "tech" -> "spirit" replacement
        return clean.replace("tech", "spirit")

    def get_scale_type(self, raw_type: str) -> str:
        """Standardize a scale type string."""
        if raw_type in self.scale_type_map:
            return self.scale_type_map[raw_type]
        
        # Fallback
        clean = raw_type
        if clean.startswith("E"):
            clean = clean[1:]
        
        clean = re.sub(r'(?<!^)(?=[A-Z])', '_', clean).lower()
        return clean.replace("tech", "spirit")

    def get_slot_name(self, raw_slot: str) -> str:
        """Standardize a slot name."""
        return self.slot_map.get(raw_slot, raw_slot.lower().replace("eitemslottype_", ""))

# Singleton instance
MAPPING = MappingHandler(Path(__file__).parent.parent / "data" / "scale_type_mapping.txt")
