"""Jobber webhook validation and payload normalization."""
import hmac
import hashlib

from fastapi import HTTPException, Request

from config import get_settings
from models.review_request import JobCompletedEvent
from utils import normalize_phone


async def parse_jobber_event(request: Request) -> JobCompletedEvent:
    body = await request.body()
    signature = request.headers.get("X-Jobber-Signature", "")
    secret = get_settings().jobber_webhook_secret.encode()
    if secret:
        expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise HTTPException(status_code=403, detail="Invalid Jobber signature")
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
