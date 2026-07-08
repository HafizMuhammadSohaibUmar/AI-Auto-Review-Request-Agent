"""LeadPilot AI Review Request Agent."""
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, Response

from config import get_settings
from handlers.followup import run_followup_check
from handlers.job_completed import handle_job_completed
from handlers.sms_reply import handle_sms_reply
from integrations.housecallpro_webhook import parse_housecallpro_event
from integrations.jobber_webhook import parse_jobber_event
from integrations.supabase_client import supabase_client
from integrations.twilio_client import twilio_client, validate_twilio_request
from logging_utils import log_event, setup_logging
from models.review_request import JobCompletedEvent
from scheduler import start_scheduler, stop_scheduler
from services.sentiment import health_check as sentiment_health_check
from utils import normalize_phone

logger = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    start_scheduler()
    log_event(logger, "Review request agent starting", action="startup")
    yield
    stop_scheduler()
    log_event(logger, "Review request agent stopping", action="shutdown")


app = FastAPI(title="LeadPilot AI Review Request Agent", lifespan=lifespan)


@app.get("/")
async def root():
    return {
        "service": "LeadPilot AI Review Request Agent",
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
    }


@app.post("/webhook/job-completed/jobber")
async def jobber_job_completed(request: Request):
    event = await parse_jobber_event(request)
    return await handle_job_completed(event)


@app.post("/webhook/job-completed/housecallpro")
async def housecallpro_job_completed(request: Request):
    event = await parse_housecallpro_event(request)
    return await handle_job_completed(event)


@app.post("/webhook/job-completed")
async def generic_job_completed(event: JobCompletedEvent):
    event.customer_phone = normalize_phone(event.customer_phone)
    return await handle_job_completed(event)


@app.post("/manual-trigger")
async def manual_trigger(event: JobCompletedEvent):
    event.provider = "manual"
    event.customer_phone = normalize_phone(event.customer_phone)
    return await handle_job_completed(event)


@app.post("/sms/reply")
async def sms_reply(form: dict = Depends(validate_twilio_request)):
    result = await handle_sms_reply(form)
    return Response(content="<Response/>", media_type="application/xml",
                    headers={"X-LeadPilot-Status": result["status"]})


@app.post("/followup/run")
async def followup_run():
    return await run_followup_check()


@app.get("/metrics")
async def metrics():
    return await supabase_client.metrics()


@app.get("/health")
async def health():
    sentiment, db, twilio = await sentiment_health_check(), await supabase_client.health_check(), await twilio_client.health_check()
    all_ok = sentiment.get("ok") and db.get("ok") and twilio.get("ok")
    return {
        "status": "healthy" if all_ok else "degraded",
        "business_id": get_settings().business_id,
        "sentiment": sentiment,
        "database": db,
        "twilio": twilio,
    }


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("main:app", host=settings.host, port=settings.port)
