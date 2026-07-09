"""Job completed workflow handler."""
from datetime import datetime, timezone
import logging

from config import get_settings
from integrations.supabase_client import supabase_client
from integrations.twilio_client import twilio_client
from models.review_request import JobCompletedEvent, ReviewOutcome, ReviewRequestRecord, Sentiment
from services.sentiment import classify_sentiment
from services.sms_builder import negative_feedback_sms, owner_alert_sms, review_request_sms

logger = logging.getLogger("job_completed")


async def handle_job_completed(event: JobCompletedEvent, sentiment_override: Sentiment | None = None) -> dict:
    settings = get_settings()

    if await supabase_client.is_suppressed(event.customer_phone):
        return {"status": "suppressed", "outcome": ReviewOutcome.SUPPRESSED}

    if await supabase_client.recently_requested(event.customer_phone):
        return {"status": "deduped", "outcome": ReviewOutcome.DEDUPED}

    sentiment = sentiment_override or await classify_sentiment(event.job_notes)
    now = datetime.now(timezone.utc)

    if sentiment == Sentiment.NEGATIVE:
        customer_sent = await twilio_client.send_sms(
            event.customer_phone,
            negative_feedback_sms(event),
            job_id=event.job_id,
        )
        owner_sent = await twilio_client.send_sms(
            settings.owner_phone_number,
            owner_alert_sms(event, sentiment.value),
            job_id=event.job_id,
        )
        outcome = ReviewOutcome.FEEDBACK_REQUEST_SENT if customer_sent and owner_sent else ReviewOutcome.ERROR
        review_sms_sent = False
        review_sms_sent_at = None
    else:
        review_sms_sent = await twilio_client.send_sms(
            event.customer_phone,
            review_request_sms(event, sentiment),
            job_id=event.job_id,
        )
        outcome = ReviewOutcome.REVIEW_REQUEST_SENT if review_sms_sent else ReviewOutcome.ERROR
        review_sms_sent_at = now if review_sms_sent else None

    record = ReviewRequestRecord(
        business_id=settings.business_id,
        customer_phone=event.customer_phone,
        customer_name=event.customer_name,
        job_id=event.job_id,
        job_type=event.job_type,
        technician_name=event.technician_name,
        sentiment=sentiment,
        review_sms_sent=review_sms_sent,
        review_sms_sent_at=review_sms_sent_at,
        outcome=outcome,
    )
    await supabase_client.insert_review_request(record)
    return {"status": "ok", "sentiment": sentiment, "outcome": outcome}
