# Deadlock RAG Data Pipeline

## Overview
This project is a Python-based data pipeline designed to parse and extract information from Valve's KeyValues3 (`.vdata`) game files for the game Deadlock. The goal is to clean, normalize, and merge this data into a structured JSON format suitable for analytical tasks and Retrieval-Augmented Generation (RAG) systems.

## Key Directories & Files
- `data/` - Contains raw and processed data.
  - `heroes.vdata` & `abilities.vdata`: Raw KV3 input files containing game definitions.
  - `processed_heroes.json`: The primary output file containing normalized hero profiles and enriched ability data.
  - `shop.json`: The secondary output file containing global item purchase bonuses (investment bonuses), will contain info about all items in the game.
  - `report.txt`: A brief summary of the last pipeline run.
- `src/heroes_abilities_extractor/` - The Python source code for the pipeline.
  - `kv3_parser.py`: A custom token-based recursive descent parser for Valve's KV3 format. It handles nested blocks, strips resource prefixes (`panorama:`, `subclass:`), and normalizes numeric/boolean values.
  - `hero_extractor.py`: Extracts hero profiles from the parsed KV3 data. Handles "stat inheritance" by pulling missing baseline stats from the `hero_base` object and renaming fields using internal mappings.
  - `ability_enricher.py` (and semantic tagging logic): Performs a join between a hero's `signature_abilities` list and the data in `abilities.vdata`. Extracts property modifiers (e.g., `DPS`, `AbilityCooldown`) and scaling multipliers. Automatically applies semantic tags (`[Spirit]`, `[DoT]`, `[Mobility]`).
  - `pipeline.py`: The main orchestrator script that ties the parsing, extraction, and file generation steps together.
  - `validate_output.py`: A test script containing assertions to verify the integrity and schema of the generated pipeline outputs.
- `convert_hero.py`: A legacy prototype script kept for reference.

## Architectural Notes
1. **Parser Implementation**: The `kv3_parser.py` uses a custom `_Scanner` and `_Parser` rather than a generic KV3 library due to specific syntax quirks in the `.vdata` files (e.g., prefix dropping, missing top-level braces, implicit arrays).
2. **Stat Inheritance**: Many heroes lack explicit baseline stats in their raw `.vdata` block. `hero_extractor.py` intentionally overlays a hero's specific stats on top of `hero_base` to ensure complete profiles.
3. **Semantic Tagging**: Tags like `[Spirit]` or `[DoT]` are generated dynamically via rule-based checks on ability properties (e.g., triggering on the `scale_function_tech_damage` class or `tech_damage` CSS class).
4. **Data Deduplication**: Shop investment bonuses (`m_mapPurchaseBonuses`) were found to be identical across all heroes. They are extracted globally from `hero_base` into `shop.json` rather than bloating individual hero entries.

## Usage
To run the full pipeline and regenerate the JSON outputs:
```bash
python src/heroes_abilities_extractor/pipeline.py
```

To verify the generated JSON against the expected schema rules:
```bash
python src/heroes_abilities_extractor/validate_output.py
```
