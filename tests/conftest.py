import sys
from pathlib import Path

# Allow relative imports inside src/heroes_abilities_extractor and src/shop_extractor
# (e.g. `from utils import ...`) to resolve when tests are run from project root.
_src = Path(__file__).parent.parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))
for sub in ("heroes_abilities_extractor", "shop_extractor"):
    d = str(_src / sub)
    if d not in sys.path:
        sys.path.insert(0, d)
