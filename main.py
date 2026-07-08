"""LeadPilot AI Review Request Agent."""
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import HTMLResponse

from config import get_settings
from handlers.demo import demo_page, demo_trigger
from handlers.followup import run_followup_check
from handlers.job_completed import handle_job_completed
from handlers.sms_reply import handle_sms_reply
from integrations.housecallpro_webhook import parse_housecallpro_event
from integrations.jobber_webhook import parse_jobber_event
from integrations.supabase_client import supabase_client
from integrations.twilio_client import twilio_client, validate_twilio_request
from integrations.webhook_security import require_api_key, require_hmac_signature
from logging_utils import log_event, setup_logging
from models.review_request import JobCompletedEvent
from scheduler import start_scheduler, stop_scheduler
from services.review_tracker import review_tracker
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


@app.get("/demo", response_class=HTMLResponse)
async def browser_demo():
    return await demo_page()


@app.post("/demo/trigger")
async def browser_demo_trigger(request: Request):
    return await demo_trigger(request)


@app.post("/webhook/job-completed/jobber")
async def jobber_job_completed(request: Request):
    event = await parse_jobber_event(request)
    return await handle_job_completed(event)


@app.post("/webhook/job-completed/housecallpro")
async def housecallpro_job_completed(request: Request):
    event = await parse_housecallpro_event(request)
    return await handle_job_completed(event)


@app.post("/webhook/job-completed")
async def generic_job_completed(request: Request):
    settings = get_settings()
    body = await request.body()
    require_hmac_signature(
        body=body,
        signature=request.headers.get("X-LeadPilot-Signature", ""),
        secret=settings.internal_webhook_secret,
        provider="LeadPilot internal",
    )
    event = JobCompletedEvent.model_validate_json(body)
    event.customer_phone = normalize_phone(event.customer_phone)
    return await handle_job_completed(event)


@app.post("/manual-trigger")
async def manual_trigger(request: Request):
    settings = get_settings()
    require_api_key(request, expected=settings.manual_trigger_api_key)
    event = JobCompletedEvent.model_validate(await request.json())
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
    sentiment = await sentiment_health_check()
    db = await supabase_client.health_check()
    twilio = await twilio_client.health_check()
    reviews = await review_tracker.health_check()
    all_ok = sentiment.get("ok") and db.get("ok") and twilio.get("ok") and reviews.get("ok")
    return {
        "status": "healthy" if all_ok else "degraded",
        "business_id": get_settings().business_id,
        "sentiment": sentiment,
        "database": db,
        "twilio": twilio,
        "review_tracker": reviews,
    }


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("main:app", host=settings.host, port=settings.port)
