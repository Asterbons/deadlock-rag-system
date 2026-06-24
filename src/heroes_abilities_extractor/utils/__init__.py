import re
from mapping_handler import MAPPING

# Mapping from citadel_inline_attribute names to actual property names (item descriptions)
_INLINE_ATTR_TO_PROP = {
    "BonusWeaponDamage":  "HeadShotBonusDamage",
    "BonusSpiritDamage":  "ProcBonusMagicDamage",
    "WeaponDamage":       "HeadShotBonusDamage",
    "SpiritDamage":       "ProcBonusMagicDamage",
    "Heal":               "BaseHealOnHeadshot",
    "Slow":               "SlowPercent",
    "Stun":               "StunDuration",
    "BonusFireRate":      "BonusFireRate",
    "BonusMoveSpeed":     "BonusMoveSpeed",
    "SpiritDPS":          "DotHealthPercent",
    "MeleeDamage":        "BonusDamage",
}

_HTML_TAG_RE = re.compile(r'<[^>]+>')
_G_PLACEHOLDER_RE = re.compile(r'\{g:[^}]+\}')
_PLACEHOLDER_RE = re.compile(r'\{[sgf]:([^}]+)\}')


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


def _parse_html_numeric(val):
    """Parse a value as a number, stripping a trailing unit suffix."""
    if isinstance(val, (int, float)):
        return val
    s = str(val).strip().rstrip("m%s")
    try:
        f = float(s)
        i = int(f)
        return i if f == i else round(f, 6)
    except (ValueError, OverflowError):
        return None


def strip_html(text: str, props: dict = None) -> str:
    """Strip HTML tags and template placeholders from localization text.

    With ``props``, resolves ``{s:Name}`` / ``{g:citadel_inline_attribute:'X'}`` /
    ``{f:Name}`` placeholders by reading ``m_strValue`` from the property dict,
    and collapses whitespace. Without props (legacy mode for short labels),
    drops ``{g:...}`` placeholders only and preserves internal whitespace.
    """
    if not text:
        return ""

    clean = _HTML_TAG_RE.sub('', text)

    if props is None:
        clean = _G_PLACEHOLDER_RE.sub('', clean)
        return clean.strip()

    def _resolve(m):
        raw = m.group(1)
        attr_match = re.match(r"citadel_inline_attribute:'(\w+)'", raw)
        if attr_match:
            attr_name = attr_match.group(1)
            prop_name = _INLINE_ATTR_TO_PROP.get(attr_name, attr_name)
        else:
            prop_name = raw

        prop_data = props.get(prop_name)
        if isinstance(prop_data, dict):
            val = prop_data.get("m_strValue")
            if val is not None:
                numeric = _parse_html_numeric(val)
                if numeric is not None:
                    return str(int(numeric) if isinstance(numeric, float) and numeric.is_integer() else numeric)
                return str(val)
        return ""

    clean = _PLACEHOLDER_RE.sub(_resolve, clean)
    return re.sub(r'\s+', ' ', clean).strip()

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
