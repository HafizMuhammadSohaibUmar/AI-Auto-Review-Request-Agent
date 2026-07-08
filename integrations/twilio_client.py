"""Async Twilio SMS client and webhook validation."""
import logging
from typing import Optional

import httpx
from fastapi import HTTPException, Request
from twilio.request_validator import RequestValidator

from config import get_settings
from logging_utils import Timer, log_event

logger = logging.getLogger("twilio")


class TwilioClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.account_sid = settings.twilio_account_sid
        self.auth_token = settings.twilio_auth_token
        self.from_number = settings.twilio_phone_number
        self.api_base = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}"

    async def send_sms(self, to: str, body: str, *, job_id: Optional[str] = None) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                with Timer() as timer:
                    resp = await client.post(
                        f"{self.api_base}/Messages.json",
                        auth=(self.account_sid, self.auth_token),
                        data={"To": to, "From": self.from_number, "Body": body},
                    )
                resp.raise_for_status()
            log_event(logger, "SMS sent", action="sms_sent", job_id=job_id,
                      phone=to, latency_ms=timer.latency_ms)
            return True
        except Exception as exc:
            log_event(logger, f"SMS failed: {exc}", action="sms_failed",
                      job_id=job_id, phone=to, level=logging.ERROR)
            return False

    async def health_check(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                with Timer() as timer:
                    resp = await client.get(
                        f"{self.api_base}.json",
                        auth=(self.account_sid, self.auth_token),
                    )
                resp.raise_for_status()
            return {"ok": True, "latency_ms": timer.latency_ms}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


async def validate_twilio_request(request: Request) -> dict:
    settings = get_settings()
    form = dict(await request.form())
    if not settings.validate_twilio_signature:
        return form
    signature = request.headers.get("X-Twilio-Signature", "")
    url = settings.public_base_url.rstrip("/") + request.url.path
    if request.url.query:
        url += "?" + request.url.query
    validator = RequestValidator(settings.twilio_auth_token)
    if not validator.validate(url, form, signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
    return form


twilio_client = TwilioClient()
