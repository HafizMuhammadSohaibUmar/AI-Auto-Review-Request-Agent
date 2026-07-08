"""Housecall Pro webhook validation and payload normalization."""

from fastapi import Request

from config import get_settings
from integrations.webhook_security import require_hmac_signature
from models.review_request import JobCompletedEvent
from utils import normalize_phone


async def parse_housecallpro_event(request: Request) -> JobCompletedEvent:
    settings = get_settings()
    body = await request.body()
    signature = request.headers.get(settings.housecallpro_signature_header, "")
    require_hmac_signature(
        body=body,
        signature=signature,
        secret=settings.housecallpro_webhook_secret,
        provider="Housecall Pro",
    )
    payload = await request.json()
    customer = payload.get("customer", {})
    job = payload.get("job", payload)
    return JobCompletedEvent(
        provider="housecallpro",
        customer_name=customer.get("name") or job.get("customer_name") or "",
        customer_phone=normalize_phone(customer.get("mobile_number") or job.get("customer_phone") or ""),
        technician_name=job.get("technician_name") or job.get("employee_name") or "your technician",
        job_type=job.get("job_type") or job.get("name") or "service",
        job_notes=job.get("notes") or job.get("description") or "",
        job_id=str(job.get("id") or job.get("job_id") or ""),
    )
