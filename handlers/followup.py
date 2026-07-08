"""48-hour review follow-up handling."""
from datetime import datetime, timedelta, timezone

from config import get_settings
from integrations.supabase_client import supabase_client
from integrations.twilio_client import twilio_client
from services.review_tracker import review_tracker
from services.sms_builder import followup_sms


async def run_followup_check() -> dict:
    settings = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.followup_delay_hours)
    rows = await supabase_client.due_followups(cutoff)
    sent = 0
    skipped = 0
    for row in rows:
        phone = row["customer_phone"]
        if await supabase_client.is_suppressed(phone):
            skipped += 1
            continue
        if await review_tracker.has_review_for_request(row):
            skipped += 1
            continue
        sms_sent = await twilio_client.send_sms(
            phone,
            followup_sms(row["customer_name"], row["job_type"], row["technician_name"]),
            job_id=row["job_id"],
        )
        if not sms_sent:
            skipped += 1
            continue
        await supabase_client.mark_followup_sent(row["id"])
        sent += 1
    return {"checked": len(rows), "sent": sent, "skipped": skipped}
