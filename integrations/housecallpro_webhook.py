"""Housecall Pro webhook validation and payload normalization."""
import hmac
import hashlib

from fastapi import HTTPException, Request

from config import get_settings
from models.review_request import JobCompletedEvent
from utils import normalize_phone


async def parse_housecallpro_event(request: Request) -> JobCompletedEvent:
    body = await request.body()
    signature = request.headers.get("X-HousecallPro-Signature", "")
    secret = get_settings().housecallpro_webhook_secret.encode()
    if secret:
        expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise HTTPException(status_code=403, detail="Invalid Housecall Pro signature")
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
