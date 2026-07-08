"""Sentiment classification via LiteLLM."""
import asyncio
import logging
import os

import litellm

from config import get_settings
from logging_utils import Timer, log_event
from models.review_request import Sentiment

logger = logging.getLogger("sentiment")
litellm.suppress_debug_info = True


PROMPT = (
    "Classify this job note as POSITIVE, NEUTRAL, or NEGATIVE for customer "
    "satisfaction. Job notes: {notes}. Reply with only one word."
)


async def classify_sentiment(job_notes: str) -> Sentiment:
    settings = get_settings()
    if settings.mistral_api_key:
        os.environ["MISTRAL_API_KEY"] = settings.mistral_api_key
    notes = (job_notes or "").strip() or "Job completed. No customer complaint recorded."
    try:
        with Timer() as timer:
            response = await asyncio.wait_for(
                litellm.acompletion(
                    model=settings.sentiment_model,
                    messages=[{"role": "user", "content": PROMPT.format(notes=notes)}],
                    max_tokens=3,
                    temperature=0,
                    timeout=settings.llm_timeout_seconds,
                ),
                timeout=settings.llm_timeout_seconds,
            )
        raw = (response.choices[0].message.content or "").strip().upper()
        log_event(logger, "Sentiment classified", action="sentiment_classified",
                  latency_ms=timer.latency_ms, raw=raw)
    except Exception as exc:
        log_event(logger, f"Sentiment failed, defaulting to NEUTRAL: {exc}",
                  action="sentiment_failed", level=logging.WARNING)
        return Sentiment.NEUTRAL
    if "NEGATIVE" in raw:
        return Sentiment.NEGATIVE
    if "POSITIVE" in raw:
        return Sentiment.POSITIVE
    return Sentiment.NEUTRAL


async def health_check() -> dict:
    try:
        with Timer() as timer:
            await classify_sentiment("Customer was happy with the work.")
        return {"ok": True, "latency_ms": timer.latency_ms}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
