"""Inbound SMS reply handler for opt-out handling."""
from integrations.supabase_client import supabase_client
from integrations.twilio_client import twilio_client
from services.sms_builder import opt_out_sms
from utils import is_stop_message, normalize_phone


async def handle_sms_reply(form: dict) -> dict:
    from_number = normalize_phone(form.get("From", ""))
    body = form.get("Body", "")
    message_sid = form.get("MessageSid", "")

    if is_stop_message(body):
        await supabase_client.suppress(from_number, f"twilio_stop:{message_sid}")
        await twilio_client.send_sms(from_number, opt_out_sms())
        return {"status": "suppressed"}
    return {"status": "ignored"}
