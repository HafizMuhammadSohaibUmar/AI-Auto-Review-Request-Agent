"""SMS templates for review request workflows."""
from config import get_settings
from models.review_request import JobCompletedEvent


def review_request_sms(event: JobCompletedEvent) -> str:
    settings = get_settings()
    return (
        f"Hi {event.customer_name}, thanks for choosing {settings.business_name} "
        f"for your {event.job_type}. {event.technician_name} was glad to help. "
        f"If everything went well, would you mind leaving us a quick Google review? "
        f"{settings.google_review_url} - {settings.business_name}"
    )


def negative_feedback_sms(event: JobCompletedEvent) -> str:
    settings = get_settings()
    return (
        f"Hi {event.customer_name}, thank you for trusting {settings.business_name} "
        f"with your {event.job_type}. We want every visit to feel handled properly. "
        f"If anything could have gone better, please reply here and our owner will review it. "
        f"- {settings.business_name}"
    )


def owner_alert_sms(event: JobCompletedEvent, sentiment: str) -> str:
    settings = get_settings()
    return (
        f"Review agent alert: {event.customer_name} ({event.customer_phone}) had a "
        f"{sentiment} sentiment after {event.job_type} with {event.technician_name}. "
        f"Notes: {event.job_notes or 'No notes provided'}. - {settings.business_name}"
    )


def followup_sms(customer_name: str, job_type: str) -> str:
    settings = get_settings()
    return (
        f"Hi {customer_name}, just checking in once more after your {job_type}. "
        f"If our team did a good job, your Google review would really help us: "
        f"{settings.google_review_url} - {settings.business_name}"
    )


def opt_out_sms() -> str:
    return "You are opted out and will not receive further review request texts."
