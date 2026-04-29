import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PIPELINE_STEPS = [
    ("Heroes & Abilities extraction",
     [sys.executable, "src/heroes_abilities_extractor/pipeline.py"]),
    ("Shop extraction",
     [sys.executable, "src/shop_extractor/pipeline.py"]),
    ("Wiki Scraper",
     [sys.executable, "-m", "src.wiki_scraper.pipeline"]),
    ("Image Scraper",
     [sys.executable, "-m", "src.wiki_scraper.image_scraper"]),
    ("Chunker",
     [sys.executable, "src/rag/chunker.py"]),
    ("Indexer",
     [sys.executable, "src/rag/indexer.py"]),
]


def run_full_pipeline() -> bool:
    print(f"\n{'='*50}")
    print(f"Starting full pipeline update at {datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"{'='*50}")

    for step_name, cmd in PIPELINE_STEPS:
        print(f"\n→ {step_name}...")
        try:
            subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)
        except subprocess.CalledProcessError as e:
            print(f"  FAILED: {step_name} exited with code {e.returncode}")
            print("  Pipeline aborted.")
            return False
        print(f"  Done: {step_name}")

    print(f"\n{'='*50}")
    print(f"Pipeline complete at {datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"{'='*50}\n")
    return True
