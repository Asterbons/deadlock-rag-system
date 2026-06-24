"""Single source of truth for the Neo4j graph schema.

All node labels, relationship types, constraints, and indexes are defined here.
Import these constants in graph_builder.py (Phase 2) instead of scattering string
literals across files.

SCHEMA_DOCS is human-readable and intended for use in architecture documentation.
"""

# ---------------------------------------------------------------------------
# Node labels
# ---------------------------------------------------------------------------

NODE_HERO = "Hero"
NODE_ABILITY = "Ability"
NODE_ITEM = "Item"
NODE_STAT = "Stat"
NODE_MECHANIC = "Mechanic"

# ---------------------------------------------------------------------------
# Relationship types
# ---------------------------------------------------------------------------

REL_HAS_ABILITY = "HAS_ABILITY"
REL_SCALES_WITH = "SCALES_WITH"    # Hero → Stat
REL_GRANTS = "GRANTS"              # Item → Stat
REL_HAS_MECHANIC = "HAS_MECHANIC"  # Item or Ability → Mechanic
REL_UPGRADES_TO = "UPGRADES_TO"    # Item → Item (craft tree)
REL_COUNTERS = "COUNTERS"          # Item → Hero | Item → Mechanic | Item → Item

# ---------------------------------------------------------------------------
# Schema documentation — used in architecture README and query tooling
# ---------------------------------------------------------------------------

SCHEMA_DOCS = [
    {
        "type": REL_HAS_ABILITY,
        "source": NODE_HERO,
        "target": NODE_ABILITY,
        "properties": [],
        "derivation": "manual",
        "example": (
            "MATCH (h:Hero {name:'Infernus'})-[:HAS_ABILITY]->(a:Ability) "
            "RETURN a.name"
        ),
    },
    {
        "type": REL_SCALES_WITH,
        "source": NODE_HERO,
        "target": NODE_STAT,
        "properties": ["scale_factor"],
        "derivation": "manual",
        "example": (
            "MATCH (h:Hero {name:'Yamato'})-[r:SCALES_WITH]->(s:Stat) "
            "RETURN s.name, r.scale_factor"
        ),
    },
    {
        "type": REL_GRANTS,
        "source": NODE_ITEM,
        "target": NODE_STAT,
        "properties": ["value", "is_percentage"],
        "derivation": "manual",
        "example": (
            "MATCH (i:Item {name:'Enduring Speed'})-[r:GRANTS]->(s:Stat) "
            "RETURN s.name, r.value, r.is_percentage"
        ),
    },
    {
        "type": REL_HAS_MECHANIC,
        "source": NODE_ITEM,
        "target": NODE_MECHANIC,
        "properties": [],
        "derivation": "manual",
        "example": (
            "MATCH (i:Item)-[:HAS_MECHANIC]->(m:Mechanic {name:'slow'}) "
            "RETURN i.name"
        ),
    },
    {
        "type": REL_UPGRADES_TO,
        "source": NODE_ITEM,
        "target": NODE_ITEM,
        "properties": ["souls_cost"],
        "derivation": "manual",
        "example": (
            "MATCH (i:Item {name:'Healing Booster'})-[r:UPGRADES_TO]->(j:Item) "
            "RETURN j.name, r.souls_cost"
        ),
    },
    {
        "type": REL_COUNTERS,
        "source": NODE_ITEM,
        "target": NODE_HERO,
        "properties": ["weight", "notes"],
        "derivation": "manual",
        "example": (
            "MATCH (i:Item {name:'Metal Skin'})-[r:COUNTERS]->(h:Hero) "
            "RETURN h.name, r.weight"
        ),
    },
    {
        "type": REL_COUNTERS,
        "source": NODE_ITEM,
        "target": NODE_MECHANIC,
        "properties": ["weight", "weight_label", "notes"],
        "derivation": "manual",
        "example": (
            "MATCH (i:Item {name:'Healbane'})-[r:COUNTERS]->(m:Mechanic) "
            "RETURN m.name, r.weight, r.notes"
        ),
    },
    {
        "type": REL_COUNTERS,
        "source": NODE_ITEM,
        "target": NODE_ITEM,
        "properties": ["weight", "weight_label", "notes"],
        "derivation": "manual",
        "example": (
            "MATCH (i:Item {name:'Armor Piercing Rounds'})-[r:COUNTERS]->(t:Item) "
            "RETURN t.name, r.weight, r.notes"
        ),
    },
]

# ---------------------------------------------------------------------------
# Constraints — executed at graph initialization
# ---------------------------------------------------------------------------

CONSTRAINTS = [
    "CREATE CONSTRAINT hero_name IF NOT EXISTS FOR (h:Hero) REQUIRE h.name IS UNIQUE",
    "CREATE CONSTRAINT ability_id IF NOT EXISTS FOR (a:Ability) REQUIRE a.id IS UNIQUE",
    "CREATE CONSTRAINT item_name IF NOT EXISTS FOR (i:Item) REQUIRE i.name IS UNIQUE",
    "CREATE CONSTRAINT stat_name IF NOT EXISTS FOR (s:Stat) REQUIRE s.name IS UNIQUE",
    "CREATE CONSTRAINT mechanic_name IF NOT EXISTS FOR (m:Mechanic) REQUIRE m.name IS UNIQUE",
]

# ---------------------------------------------------------------------------
# Indexes — executed at graph initialization
# ---------------------------------------------------------------------------

INDEXES = [
    "CREATE INDEX hero_role IF NOT EXISTS FOR (h:Hero) ON (h.role)",
    "CREATE INDEX item_tier IF NOT EXISTS FOR (i:Item) ON (i.tier)",
    "CREATE INDEX item_category IF NOT EXISTS FOR (i:Item) ON (i.category)",
]
