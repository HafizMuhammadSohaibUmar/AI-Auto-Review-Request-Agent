from unittest.mock import AsyncMock, patch

import pytest

import handlers.job_completed as job_completed
from models.review_request import JobCompletedEvent, ReviewOutcome, Sentiment


def event(notes="great work"):
    return JobCompletedEvent(
        customer_name="Jane Doe",
        customer_phone="+15559998888",
        technician_name="Alex",
        job_type="AC repair",
        job_notes=notes,
        job_id="job-1",
    )


@pytest.mark.asyncio
async def test_positive_sends_review_request():
    with patch.object(job_completed.supabase_client, "is_suppressed", new=AsyncMock(return_value=False)), \
         patch.object(job_completed.supabase_client, "recently_requested", new=AsyncMock(return_value=False)), \
         patch.object(job_completed, "classify_sentiment", new=AsyncMock(return_value=Sentiment.POSITIVE)), \
         patch.object(job_completed.twilio_client, "send_sms", new=AsyncMock(return_value=True)) as sms, \
         patch.object(job_completed.supabase_client, "insert_review_request", new=AsyncMock(return_value={})):
        result = await job_completed.handle_job_completed(event())

    assert result["outcome"] == ReviewOutcome.REVIEW_REQUEST_SENT
    assert sms.await_count == 1


@pytest.mark.asyncio
async def test_neutral_sends_review_request():
    with patch.object(job_completed.supabase_client, "is_suppressed", new=AsyncMock(return_value=False)), \
         patch.object(job_completed.supabase_client, "recently_requested", new=AsyncMock(return_value=False)), \
         patch.object(job_completed, "classify_sentiment", new=AsyncMock(return_value=Sentiment.NEUTRAL)), \
         patch.object(job_completed.twilio_client, "send_sms", new=AsyncMock(return_value=True)) as sms, \
         patch.object(job_completed.supabase_client, "insert_review_request", new=AsyncMock(return_value={})):
        result = await job_completed.handle_job_completed(event())

    assert result["outcome"] == ReviewOutcome.REVIEW_REQUEST_SENT
    assert sms.await_count == 1


@pytest.mark.asyncio
async def test_negative_sends_feedback_and_owner_alert():
    with patch.object(job_completed.supabase_client, "is_suppressed", new=AsyncMock(return_value=False)), \
         patch.object(job_completed.supabase_client, "recently_requested", new=AsyncMock(return_value=False)), \
         patch.object(job_completed, "classify_sentiment", new=AsyncMock(return_value=Sentiment.NEGATIVE)), \
         patch.object(job_completed.twilio_client, "send_sms", new=AsyncMock(return_value=True)) as sms, \
         patch.object(job_completed.supabase_client, "insert_review_request", new=AsyncMock(return_value={})):
        result = await job_completed.handle_job_completed(event("customer unhappy"))

    assert result["outcome"] == ReviewOutcome.FEEDBACK_REQUEST_SENT
    assert sms.await_count == 2


@pytest.mark.asyncio
async def test_dedup_skips_sms():
    with patch.object(job_completed.supabase_client, "is_suppressed", new=AsyncMock(return_value=False)), \
         patch.object(job_completed.supabase_client, "recently_requested", new=AsyncMock(return_value=True)), \
         patch.object(job_completed.twilio_client, "send_sms", new=AsyncMock()) as sms:
        result = await job_completed.handle_job_completed(event())

    assert result["outcome"] == ReviewOutcome.DEDUPED
    sms.assert_not_awaited()
