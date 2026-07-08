import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.update({
    "BUSINESS_ID": "test-business",
    "BUSINESS_NAME": "Test HVAC Co",
    "PUBLIC_BASE_URL": "http://testserver",
    "TWILIO_ACCOUNT_SID": "ACtest",
    "TWILIO_AUTH_TOKEN": "test_auth",
    "TWILIO_PHONE_NUMBER": "+15550001111",
    "OWNER_PHONE_NUMBER": "+15550002222",
    "VALIDATE_TWILIO_SIGNATURE": "true",
    "SMS_DRY_RUN": "true",
    "MISTRAL_API_KEY": "test_mistral",
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_KEY": "sb_test",
    "GBP_PLACE_ID": "place123",
    "JOBBER_WEBHOOK_SECRET": "jobber_secret",
    "HOUSECALLPRO_WEBHOOK_SECRET": "hcp_secret",
    "INTERNAL_WEBHOOK_SECRET": "internal_secret",
    "MANUAL_TRIGGER_API_KEY": "manual_key",
    "DEMO_MODE_ENABLED": "true",
})

import pytest
from twilio.request_validator import RequestValidator


@pytest.fixture
def twilio_signature():
    validator = RequestValidator(os.environ["TWILIO_AUTH_TOKEN"])

    def _sign(url: str, params: dict) -> str:
        return validator.compute_signature(url, params)

    return _sign
