import json
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from integrations.webhook_security import hmac_sha256_signature
from main import app
from models.review_request import ReviewOutcome


def payload() -> dict:
    return {
        "customer_name": "Jane Doe",
        "customer_phone": "(555) 999-8888",
        "technician_name": "Alex",
        "job_type": "AC repair",
        "job_notes": "Great visit",
        "job_id": "job-1",
    }


def test_generic_webhook_requires_valid_internal_signature():
    body = json.dumps(payload(), separators=(",", ":")).encode()
    signature = hmac_sha256_signature("internal_secret", body)
    client = TestClient(app)
    with patch("main.handle_job_completed", new=AsyncMock(return_value={
        "status": "ok",
        "outcome": ReviewOutcome.REVIEW_REQUEST_SENT,
    })) as handler:
        response = client.post(
            "/webhook/job-completed",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-LeadPilot-Signature": signature,
            },
        )

    assert response.status_code == 200
    handler.assert_awaited_once()


def test_generic_webhook_rejects_bad_signature():
    client = TestClient(app)
    response = client.post(
        "/webhook/job-completed",
        json=payload(),
        headers={"X-LeadPilot-Signature": "bad"},
    )

    assert response.status_code == 403


def test_manual_trigger_requires_api_key():
    client = TestClient(app)
    response = client.post("/manual-trigger", json=payload())

    assert response.status_code == 403


def test_manual_trigger_accepts_api_key():
    client = TestClient(app)
    with patch("main.handle_job_completed", new=AsyncMock(return_value={
        "status": "ok",
        "outcome": ReviewOutcome.REVIEW_REQUEST_SENT,
    })) as handler:
        response = client.post(
            "/manual-trigger",
            json=payload(),
            headers={"X-LeadPilot-Key": "manual_key"},
        )

    assert response.status_code == 200
    handler.assert_awaited_once()
