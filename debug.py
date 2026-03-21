import sys
sys.path.insert(0, './src/heroes_abilities_extractor')
sys.path.insert(0, './src')
from kv3_parser import parse_kv3_file
from pathlib import Path
import pprint
data = parse_kv3_file(Path('data/raw/abilities.vdata'))
props = data.get('viscous_telepunch', {}).get('m_mapAbilityProperties', {})
pprint.pprint(props)
