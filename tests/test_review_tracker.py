from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from services.review_tracker import ReviewTracker


@pytest.mark.asyncio
async def test_review_tracker_matches_customer_review_after_request():
    tracker = ReviewTracker()
    tracker.settings.gbp_account_id = "acct"
    tracker.settings.gbp_location_id = "loc"
    tracker.settings.gbp_access_token = "token"
    row = {
        "customer_name": "Jane Doe",
        "review_sms_sent_at": datetime(2026, 7, 9, tzinfo=timezone.utc).isoformat(),
    }
    reviews = [{
        "reviewer": {"displayName": "Jane Doe"},
        "updateTime": "2026-07-10T12:00:00Z",
    }]

    with patch.object(tracker, "_recent_reviews", new=AsyncMock(return_value=reviews)):
        assert await tracker.has_review_for_request(row) is True


@pytest.mark.asyncio
async def test_review_tracker_does_not_match_different_customer():
    tracker = ReviewTracker()
    row = {
        "customer_name": "Jane Doe",
        "review_sms_sent_at": datetime(2026, 7, 9, tzinfo=timezone.utc).isoformat(),
    }
    reviews = [{
        "reviewer": {"displayName": "Sam Smith"},
        "updateTime": "2026-07-10T12:00:00Z",
    }]

    with patch.object(tracker, "_recent_reviews", new=AsyncMock(return_value=reviews)):
        assert await tracker.has_review_for_request(row) is False
