"""Google Business Profile review tracking."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import httpx

from config import get_settings


class ReviewTracker:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def configured(self) -> bool:
        return bool(
            self.settings.gbp_account_id
            and self.settings.gbp_location_id
            and self.settings.gbp_access_token
        )

    async def _recent_reviews(self) -> list[Dict[str, Any]]:
        if not self.configured:
            return []
        parent = f"accounts/{self.settings.gbp_account_id}/locations/{self.settings.gbp_location_id}"
        url = f"https://mybusiness.googleapis.com/v4/{parent}/reviews"
        headers = {"Authorization": f"Bearer {self.settings.gbp_access_token}"}
        params = {"pageSize": "50", "orderBy": "updateTime desc"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
        return response.json().get("reviews", [])

    @staticmethod
    def _review_author(review: Dict[str, Any]) -> str:
        reviewer = review.get("reviewer") or {}
        return (reviewer.get("displayName") or review.get("reviewerDisplayName") or "").strip().casefold()

    @staticmethod
    def _review_time(review: Dict[str, Any]) -> datetime | None:
        raw = review.get("updateTime") or review.get("createTime")
        if not raw:
            return None
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))

    async def has_review_for_request(self, request_row: Dict[str, Any]) -> bool:
        customer_name = (request_row.get("customer_name") or "").strip().casefold()
        sent_at_raw = request_row.get("review_sms_sent_at") or request_row.get("created_at")
        if not customer_name or not sent_at_raw:
            return False
        sent_at = datetime.fromisoformat(str(sent_at_raw).replace("Z", "+00:00"))
        oldest_match = sent_at - timedelta(days=1)
        newest_match = datetime.now(timezone.utc) + timedelta(days=self.settings.gbp_review_match_window_days)
        for review in await self._recent_reviews():
            review_time = self._review_time(review)
            if not review_time or review_time < oldest_match or review_time > newest_match:
                continue
            author = self._review_author(review)
            if author and (author == customer_name or customer_name in author or author in customer_name):
                return True
        return False

    async def has_review_for_job(self, customer_phone: str, job_id: str) -> bool:
        """Backward-compatible API; GBP reviews cannot expose phone or job ids."""
        return False

    async def health_check(self) -> dict:
        if not self.configured:
            return {"ok": True, "configured": False}
        try:
            reviews = await self._recent_reviews()
            return {"ok": True, "configured": True, "recent_reviews_seen": len(reviews)}
        except Exception as exc:
            return {"ok": False, "configured": True, "error": str(exc)}


review_tracker = ReviewTracker()
