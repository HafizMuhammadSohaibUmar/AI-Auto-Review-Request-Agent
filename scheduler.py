"""APScheduler setup for follow-up processing."""
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
except ImportError:
    AsyncIOScheduler = None

from handlers.followup import run_followup_check


class DisabledScheduler:
    running = False

    def add_job(self, *args, **kwargs) -> None:
        return None

    def start(self) -> None:
        return None

    def shutdown(self, wait: bool = False) -> None:
        return None


scheduler = AsyncIOScheduler() if AsyncIOScheduler else DisabledScheduler()


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.add_job(run_followup_check, "interval", minutes=30,
                          id="review_followup_check", replace_existing=True)
        scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
