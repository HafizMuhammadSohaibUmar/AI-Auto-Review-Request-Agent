from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from main import app
from models.review_request import ReviewOutcome, Sentiment


def demo_payload(notes: str = "Customer was happy with the work.") -> dict:
    return {
        "customer_name": "Jane Doe",
        "customer_phone": "+15559998888",
        "technician_name": "Alex",
        "job_type": "AC repair",
        "job_notes": notes,
        "job_id": "demo-job-1",
    }


def test_demo_page_loads():
    client = TestClient(app)
    response = client.get("/demo")

    assert response.status_code == 200
    assert "LeadPilot AI Review Request Agent" in response.text
    assert "Happy customer" in response.text


def test_demo_trigger_returns_review_sms_preview_in_dry_run():
    client = TestClient(app)
    with patch("handlers.demo.handle_job_completed", new=AsyncMock(return_value={
        "status": "ok",
        "sentiment": Sentiment.POSITIVE,
        "outcome": ReviewOutcome.REVIEW_REQUEST_SENT,
    })) as handler:
        response = client.post("/demo/trigger", json=demo_payload())

    body = response.json()
    assert response.status_code == 200
    assert body["sms_mode"] == "dry_run"
    assert body["result"]["outcome"] == ReviewOutcome.REVIEW_REQUEST_SENT
    assert len(body["sms_preview"]) == 1
    assert "Google review" in body["sms_preview"][0]["body"]
    handler.assert_awaited_once()


def test_demo_trigger_returns_negative_feedback_preview():
    client = TestClient(app)
    with patch("handlers.demo.handle_job_completed", new=AsyncMock(return_value={
        "status": "ok",
        "sentiment": Sentiment.NEGATIVE,
        "outcome": ReviewOutcome.FEEDBACK_REQUEST_SENT,
    })):
        response = client.post("/demo/trigger", json=demo_payload("Customer was frustrated."))

    body = response.json()
    assert response.status_code == 200
    assert len(body["sms_preview"]) == 2
    assert "owner will review it" in body["sms_preview"][0]["body"]
