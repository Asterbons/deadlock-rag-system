import re
from mapping_handler import MAPPING

def camel_to_snake(name: str) -> str:
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
    s = re.sub(r'([a-z\d])([A-Z])', r'\1_\2', s)
    return re.sub(r'_+', '_', s).lower().strip('_')

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

def get_stat_name(raw_key, stat_labels=None):
    if stat_labels and raw_key in stat_labels:
        label = stat_labels[raw_key].get("label", "")
        if label:
            # Convert "Movement Speed" to "movement_speed"
            clean = label.lower().replace(" ", "_")
            return re.sub(r'[^a-z0-9_]', '', clean)
    return MAPPING.get_stat_name(raw_key)
