import logging
import requests
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.config import DATA_DIR, RAW_DATA_DIR

logger = logging.getLogger(__name__)

REPO = "SteamTracking/GameTracking-Deadlock"
GITHUB_API = f"https://api.github.com/repos/{REPO}/commits"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/master"

WATCHED_FILES = {
    "abilities":      "game/citadel/pak01_dir/scripts/abilities.vdata",
    "heroes":         "game/citadel/pak01_dir/scripts/heroes.vdata",
    "loc_hero_names": "game/citadel/pak01_dir/resource/localization/citadel_gc_hero_names_english.txt",
    "loc_heroes":     "game/citadel/pak01_dir/resource/localization/citadel_heroes_english.txt",
    "loc_attributes": "game/citadel/pak01_dir/resource/localization/citadel_attributes_english.txt",
    "loc_mods":       "game/citadel/pak01_dir/resource/localization/citadel_mods_english.txt",
}

LOCAL_FILES = {
    "abilities":      RAW_DATA_DIR / "abilities.vdata",
    "heroes":         RAW_DATA_DIR / "heroes.vdata",
    "loc_hero_names": RAW_DATA_DIR / "citadel_gc_hero_names_english.txt",
    "loc_heroes":     RAW_DATA_DIR / "citadel_heroes_english.txt",
    "loc_attributes": RAW_DATA_DIR / "citadel_attributes_english.txt",
    "loc_mods":       RAW_DATA_DIR / "citadel_mods_english.txt",
}

LAST_SHA_FILE = DATA_DIR / ".last_commit_sha"

HEADERS = {"Accept": "application/vnd.github.v3+json"}


def get_latest_commit_sha() -> str:
    resp = requests.get(GITHUB_API, params={"per_page": 1}, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()[0]["sha"]


def get_last_known_sha() -> str | None:
    try:
        return LAST_SHA_FILE.read_text().strip()
    except FileNotFoundError:
        return None


def save_sha(sha: str):
    LAST_SHA_FILE.write_text(sha)


def get_changed_files(old_sha: str, new_sha: str) -> list[str]:
    url = f"https://api.github.com/repos/{REPO}/compare/{old_sha}...{new_sha}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code != 200:
        # Fallback: assume all watched files changed (compare may fail for very large diffs)
        return list(WATCHED_FILES.values())
    data = resp.json()
    # GitHub truncates comparisons >300 files; if truncated, treat as full update
    if data.get("status") == "diverged" or len(data.get("files", [])) == 300:
        return list(WATCHED_FILES.values())
    return [f["filename"] for f in data.get("files", [])]


def should_reindex(changed_files: list[str]) -> bool:
    watched = set(WATCHED_FILES.values())
    return any(f in watched for f in changed_files)


def download_game_files():
    logger.info("Downloading updated game files...")
    for key, remote_path in WATCHED_FILES.items():
        url = f"{RAW_BASE}/{remote_path}"
        local_path = LOCAL_FILES[key]
        local_path.parent.mkdir(parents=True, exist_ok=True)

        resp = requests.get(url, timeout=60)
        if resp.status_code == 200:
            local_path.write_bytes(resp.content)
            logger.info("  Downloaded: %s", local_path)
        else:
            logger.warning("  Failed to download %s (%s)", remote_path, resp.status_code)


def check_and_update() -> bool:
    """Check GitHub for new commits and download+reindex if relevant files changed."""
    logger.info("Checking for Deadlock game updates...")
    try:
        latest_sha = get_latest_commit_sha()
        known_sha = get_last_known_sha()

        if known_sha is None:
            logger.info("No previous version known — downloading all files.")
            download_game_files()
            save_sha(latest_sha)
            return True

        if latest_sha == known_sha:
            logger.info("No updates. Current: %s", latest_sha[:8])
            return False

        logger.info("New commit detected: %s → %s", known_sha[:8], latest_sha[:8])
        changed = get_changed_files(known_sha, latest_sha)
        relevant = [f for f in changed if f in WATCHED_FILES.values()]
        logger.info("Changed watched files: %s", relevant)

        if should_reindex(changed):
            logger.info("Relevant files changed — downloading and reindexing.")
            download_game_files()
            save_sha(latest_sha)
            return True
        else:
            logger.info("No relevant files changed. Updating SHA only.")
            save_sha(latest_sha)
            return False

    except Exception as e:
        logger.error("Patch monitor failed: %s", e)
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    from src.updater.update_pipeline import run_full_pipeline
    has_update = check_and_update()
    if has_update:
        run_full_pipeline()
