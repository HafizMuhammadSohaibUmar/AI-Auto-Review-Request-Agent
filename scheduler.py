"""APScheduler setup for follow-up processing."""
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from handlers.followup import run_followup_check


scheduler = AsyncIOScheduler()


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.add_job(run_followup_check, "interval", minutes=30,
                          id="review_followup_check", replace_existing=True)
        scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
