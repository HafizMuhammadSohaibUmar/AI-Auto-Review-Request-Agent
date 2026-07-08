from unittest.mock import AsyncMock, patch

import pytest

import handlers.sms_reply as sms_reply


@pytest.mark.asyncio
async def test_stop_reply_creates_suppression_and_confirms_opt_out():
    form = {
        "From": "+15559998888",
        "Body": "STOP",
        "MessageSid": "SM123",
    }
    with patch.object(sms_reply.supabase_client, "suppress", new=AsyncMock()) as suppress, \
         patch.object(sms_reply.twilio_client, "send_sms", new=AsyncMock(return_value=True)) as send:
        result = await sms_reply.handle_sms_reply(form)

    assert result == {"status": "suppressed"}
    suppress.assert_awaited_once_with("+15559998888", "twilio_stop:SM123")
    send.assert_awaited_once()


@pytest.mark.asyncio
async def test_non_stop_reply_is_ignored():
    form = {
        "From": "+15559998888",
        "Body": "Thanks",
        "MessageSid": "SM124",
    }
    with patch.object(sms_reply.supabase_client, "suppress", new=AsyncMock()) as suppress, \
         patch.object(sms_reply.twilio_client, "send_sms", new=AsyncMock()) as send:
        result = await sms_reply.handle_sms_reply(form)

    assert result == {"status": "ignored"}
    suppress.assert_not_awaited()
    send.assert_not_awaited()
