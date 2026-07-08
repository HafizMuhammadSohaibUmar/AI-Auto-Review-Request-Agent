"""Jobber webhook validation and payload normalization."""

from fastapi import Request

from config import get_settings
from integrations.webhook_security import require_hmac_signature
from models.review_request import JobCompletedEvent
from utils import normalize_phone


async def parse_jobber_event(request: Request) -> JobCompletedEvent:
    settings = get_settings()
    body = await request.body()
    signature = request.headers.get(settings.jobber_signature_header, "")
    require_hmac_signature(
        body=body,
        signature=signature,
        secret=settings.jobber_webhook_secret,
        provider="Jobber",
    )
    payload = await request.json()
    data = payload.get("data", payload)
    return JobCompletedEvent(
        provider="jobber",
        customer_name=data.get("customer_name") or data.get("client_name") or "",
        customer_phone=normalize_phone(data.get("customer_phone") or data.get("phone") or ""),
        technician_name=data.get("technician_name") or data.get("assigned_to") or "your technician",
        job_type=data.get("job_type") or data.get("title") or "service",
        job_notes=data.get("job_notes") or data.get("notes") or "",
        job_id=str(data.get("job_id") or data.get("id") or ""),
    )
