from apscheduler.schedulers.blocking import BlockingScheduler
from src.updater.patch_monitor import check_and_update
from src.updater.update_pipeline import run_full_pipeline
from src.config import UPDATE_INTERVAL_HOURS


def scheduled_check():
    has_update = check_and_update()
    if has_update:
        run_full_pipeline()


if __name__ == "__main__":
    print(f"Deadlock RAG Auto-updater started (every {UPDATE_INTERVAL_HOURS:g}h).")
    print("Running initial check...")
    scheduled_check()

    scheduler = BlockingScheduler()
    scheduler.add_job(scheduled_check, "interval", hours=UPDATE_INTERVAL_HOURS)
    scheduler.start()
