from unittest.mock import AsyncMock, patch

import pytest

import handlers.followup as followup


@pytest.mark.asyncio
async def test_followup_sends_due_message():
    rows = [{
        "id": "rr-1",
        "customer_phone": "+15559998888",
        "customer_name": "Jane",
        "job_type": "AC repair",
        "technician_name": "Alex",
        "job_id": "job-1",
    }]
    with patch.object(followup.supabase_client, "due_followups", new=AsyncMock(return_value=rows)), \
         patch.object(followup.supabase_client, "is_suppressed", new=AsyncMock(return_value=False)), \
         patch.object(followup.review_tracker, "has_review_for_request", new=AsyncMock(return_value=False)), \
         patch.object(followup.twilio_client, "send_sms", new=AsyncMock(return_value=True)) as sms, \
         patch.object(followup.supabase_client, "mark_followup_sent", new=AsyncMock()) as mark:
        result = await followup.run_followup_check()

    assert result == {"checked": 1, "sent": 1, "skipped": 0}
    sms.assert_awaited_once()
    mark.assert_awaited_once_with("rr-1")


@pytest.mark.asyncio
async def test_followup_skips_suppressed_number():
    rows = [{
        "id": "rr-1",
        "customer_phone": "+15559998888",
        "customer_name": "Jane",
        "job_type": "AC repair",
        "technician_name": "Alex",
        "job_id": "job-1",
    }]
    with patch.object(followup.supabase_client, "due_followups", new=AsyncMock(return_value=rows)), \
         patch.object(followup.supabase_client, "is_suppressed", new=AsyncMock(return_value=True)), \
         patch.object(followup.twilio_client, "send_sms", new=AsyncMock()) as sms:
        result = await followup.run_followup_check()

    assert result == {"checked": 1, "sent": 0, "skipped": 1}
    sms.assert_not_awaited()


@pytest.mark.asyncio
async def test_followup_does_not_mark_sent_when_sms_fails():
    rows = [{
        "id": "rr-1",
        "customer_phone": "+15559998888",
        "customer_name": "Jane",
        "job_type": "AC repair",
        "technician_name": "Alex",
        "job_id": "job-1",
    }]
    with patch.object(followup.supabase_client, "due_followups", new=AsyncMock(return_value=rows)), \
         patch.object(followup.supabase_client, "is_suppressed", new=AsyncMock(return_value=False)), \
         patch.object(followup.review_tracker, "has_review_for_request", new=AsyncMock(return_value=False)), \
         patch.object(followup.twilio_client, "send_sms", new=AsyncMock(return_value=False)), \
         patch.object(followup.supabase_client, "mark_followup_sent", new=AsyncMock()) as mark:
        result = await followup.run_followup_check()

    assert result == {"checked": 1, "sent": 0, "skipped": 1}
    mark.assert_not_awaited()


@pytest.mark.asyncio
async def test_followup_skips_when_review_detected():
    rows = [{
        "id": "rr-1",
        "customer_phone": "+15559998888",
        "customer_name": "Jane",
        "job_type": "AC repair",
        "technician_name": "Alex",
        "job_id": "job-1",
    }]
    with patch.object(followup.supabase_client, "due_followups", new=AsyncMock(return_value=rows)), \
         patch.object(followup.supabase_client, "is_suppressed", new=AsyncMock(return_value=False)), \
         patch.object(followup.review_tracker, "has_review_for_request", new=AsyncMock(return_value=True)), \
         patch.object(followup.twilio_client, "send_sms", new=AsyncMock()) as sms:
        result = await followup.run_followup_check()

    assert result == {"checked": 1, "sent": 0, "skipped": 1}
    sms.assert_not_awaited()
