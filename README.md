# Deadlock RAG Data Pipeline

This project is a Python-based data pipeline designed to parse and extract information from Valve's KeyValues3 (`.vdata`) game files for the game Deadlock. The goal is to clean, normalize, and merge this data into a structured JSON format suitable for analytical tasks and Retrieval-Augmented Generation (RAG) systems.

## Project Structure

```text
dlrag/
├── data/
│   ├── raw/                # Original Valve .vdata and .txt files
│   └── processed/          # Pipeline outputs
│       ├── heroes/         # Individual hero JSON files
│       ├── chunks.json     # RAG-ready text chunks
│       ├── heroes_index.json # Summary of all heroes
│       ├── processed_heroes.json # Unified hero data
│       └── shop.json       # Extracted shop and item data
├── src/
│   ├── heroes_abilities_extractor/
│   │   ├── kv3_parser.py   # Custom KeyValues3 recursive descent parser
│   │   ├── hero_extractor.py # Hero stat extraction with inheritance logic
│   │   ├── ability_enricher.py # Ability detail enrichment and semantic tagging
│   │   ├── pipeline.py     # Orchestrates unified hero data extraction
│   │   └── hero_profile_extractor.py # Granular extractor for individual files
│   ├── shop_extractor/
│   │   ├── shop_builder.py # Item and shop data processing
│   │   └── pipeline.py     # Shop extraction pipeline
│   ├── rag/
│   │   └── chunker.py      # RAG chunking pipeline (Hero, Ability, Item chunks)
│   └── config.py           # Centralized path and configuration management
├── PROJECT_CONTEXT.md      # High-level overview
├── research_notes.md       # Development notes and implementation details
└── README.md               # This file
```

## Data Overview

### Raw Data (`data/raw/`)
Contains original game files like `heroes.vdata` and `abilities.vdata`, along with localization files (`citadel_attributes_english.txt`, etc.).

### Processed Data (`data/processed/`)
- **`processed_heroes.json`**: A single JSON containing all heroes and their abilities.
- **`heroes/`**: Individual JSON files for each hero, used for granular access.
- **`shop.json`**: Comprehensive data on items, tiers, and stats.
- **`chunks.json`**: The final output for RAG, containing text-based representations of heroes, abilities, and items with associated metadata.

## Key Scripts & Pipelines

### 1. Hero & Ability Extraction
- **`kv3_parser.py`**: A custom parser specifically designed for Deadlock's `.vdata` format, handling its unique syntax and data types.
- **`pipeline.py`**: The main entry point to regenerate the complete hero knowledge base.
- **`hero_extractor.py`**: Handles "stat inheritance," ensuring heroes get baseline stats from `hero_base`.
- **`ability_enricher.py`**: Adds property modifiers and applies semantic tags like `[Spirit]`, `[DoT]`, or `[Mobility]`.

### 2. Shop Extraction
- **`shop_extractor/pipeline.py`**: Processes items from the raw data to produce `shop.json`.

### 3. RAG Chunking
- **`rag/chunker.py`**: Orchestrates the final transformation of processed data into chunks suitable for a vector database. It generates:
  - **Hero Chunks**: Summary of hero stats, types, and recommended items.
  - **Ability Chunks**: Detailed descriptions, stats, and effects of each hero ability.
  - **Item Chunks**: Item descriptions, tiers, stats, and proc effects.

## Usage

### Run the Full Pipeline
To regenerate all processed data:
1. Extract hero and ability data:
   ```bash
   python src/heroes_abilities_extractor/pipeline.py
   python src/heroes_abilities_extractor/hero_profile_extractor.py
   ```
2. Extract shop data:
   ```bash
   python src/shop_extractor/pipeline.py
   ```
3. Generate RAG chunks:
   ```bash
   python src/rag/chunker.py
   ```

### Verification
You can verify the integrity of the data using:
```bash
python tmp_verify_all.py
```
run assistent
```bash
python src/rag/rag.py
```
### Run the API
```bash
python src/api/server.py
```
