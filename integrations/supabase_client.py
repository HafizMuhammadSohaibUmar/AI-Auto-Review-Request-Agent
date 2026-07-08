"""Async Supabase PostgREST client."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

from config import get_settings
from logging_utils import Timer, log_event
from models.review_request import ReviewRequestRecord, ReviewOutcome, SuppressionRecord

logger = logging.getLogger("supabase")


class SupabaseClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.supabase_url.rstrip("/")
        self.business_id = settings.business_id
        self.dedup_window = timedelta(days=settings.dedup_window_days)
        self.headers = {
            "apikey": settings.supabase_key,
            "Authorization": f"Bearer {settings.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def _url(self, table: str) -> str:
        return f"{self.base_url}/rest/v1/{table}"

    async def _request(self, method: str, table: str, *,
                       params: Optional[dict] = None,
                       json: Any = None) -> List[Dict]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            with Timer() as timer:
                resp = await client.request(
                    method, self._url(table), headers=self.headers,
                    params=params, json=json,
                )
            resp.raise_for_status()
        log_event(logger, f"supabase {method} {table}", action="db_request",
                  latency_ms=timer.latency_ms)
        return resp.json() if resp.content else []

    async def is_suppressed(self, phone: str) -> bool:
        rows = await self._request(
            "GET", "review_suppressions",
            params={
                "business_id": f"eq.{self.business_id}",
                "phone": f"eq.{phone}",
                "select": "phone",
                "limit": "1",
            },
        )
        return bool(rows)

    async def suppress(self, phone: str, reason: str) -> None:
        if await self.is_suppressed(phone):
            return
        record = SuppressionRecord(
            business_id=self.business_id,
            phone=phone,
            reason=reason,
        )
        await self._request("POST", "review_suppressions",
                            json=record.model_dump(mode="json"))

    async def recently_requested(self, phone: str) -> bool:
        rows = await self._request(
            "GET", "review_requests",
            params={
                "business_id": f"eq.{self.business_id}",
                "customer_phone": f"eq.{phone}",
                "select": "created_at",
                "order": "created_at.desc",
                "limit": "1",
            },
        )
        if not rows:
            return False
        created = datetime.fromisoformat(rows[0]["created_at"].replace("Z", "+00:00"))
        return datetime.now(timezone.utc) - created < self.dedup_window

    async def insert_review_request(self, record: ReviewRequestRecord) -> Dict:
        rows = await self._request("POST", "review_requests",
                                   json=record.model_dump(mode="json"))
        return rows[0] if rows else {}

    async def due_followups(self, before: datetime) -> List[Dict]:
        return await self._request(
            "GET", "review_requests",
            params={
                "business_id": f"eq.{self.business_id}",
                "review_sms_sent": "eq.true",
                "followup_sent": "eq.false",
                "review_posted": "eq.false",
                "outcome": f"eq.{ReviewOutcome.REVIEW_REQUEST_SENT.value}",
                "review_sms_sent_at": f"lte.{before.isoformat()}",
                "select": "*",
            },
        )

    async def mark_followup_sent(self, record_id: str) -> None:
        await self._request(
            "PATCH", "review_requests",
            params={"id": f"eq.{record_id}", "business_id": f"eq.{self.business_id}"},
            json={
                "followup_sent": True,
                "followup_sent_at": datetime.now(timezone.utc).isoformat(),
                "outcome": ReviewOutcome.FOLLOWUP_SENT.value,
            },
        )

    async def metrics(self) -> dict:
        since = datetime.now(timezone.utc) - timedelta(days=7)
        rows = await self._request(
            "GET", "review_requests",
            params={
                "business_id": f"eq.{self.business_id}",
                "created_at": f"gte.{since.isoformat()}",
                "select": "sentiment,review_posted,outcome",
            },
        )
        total = len(rows)
        requests_sent = sum(1 for row in rows if row.get("outcome") == ReviewOutcome.REVIEW_REQUEST_SENT.value)
        positives = sum(1 for row in rows if row.get("sentiment") == "POSITIVE")
        negatives = sum(1 for row in rows if row.get("sentiment") == "NEGATIVE")
        posted = sum(1 for row in rows if row.get("review_posted"))
        return {
            "requests_sent_7d": requests_sent,
            "reviews_estimated_7d": posted,
            "conversion_rate": round(posted / requests_sent, 4) if requests_sent else 0,
            "positive_rate": round(positives / total, 4) if total else 0,
            "negative_rate": round(negatives / total, 4) if total else 0,
        }

    async def health_check(self) -> dict:
        try:
            with Timer() as timer:
                await self._request("GET", "review_requests",
                                    params={"select": "id", "limit": "1"})
            return {"ok": True, "latency_ms": timer.latency_ms}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


supabase_client = SupabaseClient()
