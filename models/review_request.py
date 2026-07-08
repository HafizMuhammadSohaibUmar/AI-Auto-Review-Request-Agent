"""Domain models for review request workflows."""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class Sentiment(str, Enum):
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"


class ReviewOutcome(str, Enum):
    REVIEW_REQUEST_SENT = "review_request_sent"
    FEEDBACK_REQUEST_SENT = "feedback_request_sent"
    DEDUPED = "deduped"
    SUPPRESSED = "suppressed"
    FOLLOWUP_SENT = "followup_sent"
    REVIEW_POSTED = "review_posted"
    ERROR = "error"


class JobCompletedEvent(BaseModel):
    customer_name: str
    customer_phone: str
    technician_name: str
    job_type: str
    job_notes: str = ""
    job_id: str
    provider: str = "manual"


class ReviewRequestRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    business_id: str
    customer_phone: str
    customer_name: str
    job_id: str
    job_type: str
    technician_name: str
    sentiment: Sentiment
    review_sms_sent: bool = False
    review_sms_sent_at: Optional[datetime] = None
    followup_sent: bool = False
    followup_sent_at: Optional[datetime] = None
    review_posted: bool = False
    outcome: ReviewOutcome
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SuppressionRecord(BaseModel):
    business_id: str
    phone: str
    reason: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
