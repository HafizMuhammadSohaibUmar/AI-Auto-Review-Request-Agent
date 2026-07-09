"""Safe browser demo for the review request agent."""
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse

from config import get_settings
from handlers.job_completed import handle_job_completed
from models.review_request import JobCompletedEvent, ReviewOutcome, Sentiment
from services.sms_builder import negative_feedback_sms, owner_alert_sms, review_request_sms
from utils import normalize_phone


DEMO_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LeadPilot AI Review Request Agent Demo</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #17202a;
      --muted: #5d6b7a;
      --line: #d8dee6;
      --panel: #ffffff;
      --soft: #f6f8fb;
      --accent: #0f766e;
      --warn: #b45309;
      --bad: #b91c1c;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif;
      background: var(--soft);
      color: var(--ink);
    }
    header {
      padding: 24px clamp(18px, 4vw, 44px);
      border-bottom: 1px solid var(--line);
      background: #fff;
    }
    h1 { margin: 0 0 6px; font-size: clamp(24px, 3vw, 34px); letter-spacing: 0; }
    p { color: var(--muted); line-height: 1.55; }
    main {
      display: grid;
      grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.9fr);
      gap: 18px;
      padding: 22px clamp(18px, 4vw, 44px) 40px;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
    }
    label { display: block; font-weight: 650; margin: 14px 0 6px; }
    input, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 11px 12px;
      font: inherit;
      background: #fff;
    }
    textarea { min-height: 96px; resize: vertical; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .scenarios { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0 2px; }
    button {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--ink);
      padding: 10px 12px;
      cursor: pointer;
      font-weight: 650;
    }
    button[type="submit"] { background: var(--accent); border-color: var(--accent); color: #fff; }
    .actions { display: flex; align-items: center; gap: 10px; margin-top: 16px; }
    .badge {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 4px 9px;
      background: #e6f4f1;
      color: var(--accent);
      font-size: 13px;
      font-weight: 700;
    }
    pre {
      white-space: pre-wrap;
      word-break: break-word;
      background: #0f172a;
      color: #e5eefb;
      border-radius: 8px;
      padding: 14px;
      min-height: 240px;
    }
    .sms {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      margin-top: 10px;
      background: #fbfcfe;
    }
    .sms-label {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 3px 8px;
      background: #eef2f7;
      color: var(--muted);
      font-size: 12px;
      font-weight: 750;
      margin-bottom: 8px;
    }
    @media (max-width: 860px) {
      main { grid-template-columns: 1fr; }
      .row { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <span class="badge">Demo mode</span>
    <h1>LeadPilot AI Review Request Agent</h1>
    <p>Trigger a completed home-service job and watch the agent route it to a Google review request or private feedback flow.</p>
  </header>
  <main>
    <section>
      <h2>Completed Job</h2>
      <div class="scenarios">
        <button data-scenario="positive" data-sentiment="POSITIVE" type="button">Happy customer</button>
        <button data-scenario="neutral" data-sentiment="NEUTRAL" type="button">Neutral job</button>
        <button data-scenario="negative" data-sentiment="NEGATIVE" type="button">Complaint</button>
      </div>
      <form id="demo-form">
        <input id="demo_sentiment" name="demo_sentiment" type="hidden" value="POSITIVE">
        <div class="row">
          <div>
            <label for="customer_name">Customer name</label>
            <input id="customer_name" name="customer_name" value="Jane Doe" required>
          </div>
          <div>
            <label for="customer_phone">Customer phone</label>
            <input id="customer_phone" name="customer_phone" required>
          </div>
        </div>
        <div class="row">
          <div>
            <label for="technician_name">Technician</label>
            <input id="technician_name" name="technician_name" value="Alex" required>
          </div>
          <div>
            <label for="job_type">Job type</label>
            <input id="job_type" name="job_type" value="AC repair" required>
          </div>
        </div>
        <label for="job_notes">Job notes</label>
        <textarea id="job_notes" name="job_notes" required>Customer was happy with the repair and thanked Alex before leaving.</textarea>
        <div class="actions">
          <button type="submit">Run Agent</button>
          <span id="status"></span>
        </div>
      </form>
    </section>
    <section>
      <h2>Agent Output</h2>
      <pre id="result">Run a scenario to see sentiment, routing, and SMS preview.</pre>
      <div id="messages"></div>
    </section>
  </main>
  <script>
    const scenarios = {
      positive: "Customer was happy with the repair and thanked Alex before leaving.",
      neutral: "Job completed successfully. No complaint was recorded.",
      negative: "Customer said the issue was not fully fixed and was frustrated about the visit."
    };
    function nextDemoPhone() {
      return "+1555" + String(Date.now()).slice(-7);
    }
    document.getElementById("customer_phone").value = nextDemoPhone();
    document.querySelectorAll("[data-scenario]").forEach((button) => {
      button.addEventListener("click", () => {
        document.getElementById("job_notes").value = scenarios[button.dataset.scenario];
        document.getElementById("demo_sentiment").value = button.dataset.sentiment;
        document.getElementById("customer_phone").value = nextDemoPhone();
      });
    });
    document.getElementById("demo-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const status = document.getElementById("status");
      const result = document.getElementById("result");
      const messages = document.getElementById("messages");
      status.textContent = "Running...";
      messages.innerHTML = "";
      const data = Object.fromEntries(new FormData(event.target).entries());
      data.job_id = "demo-" + Date.now();
      data.customer_phone = nextDemoPhone();
      document.getElementById("customer_phone").value = data.customer_phone;
      const response = await fetch("/demo/trigger", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data)
      });
      const body = await response.json();
      result.textContent = JSON.stringify(body, null, 2);
      if (body.sms_preview) {
        messages.innerHTML = body.sms_preview.map((sms) => `<div class="sms"><span class="sms-label">${sms.label}</span><br><strong>${sms.to}</strong><p>${sms.body}</p></div>`).join("");
      }
      status.textContent = response.ok ? "Done" : "Failed";
    });
  </script>
</body>
</html>"""


async def demo_page() -> HTMLResponse:
    if not get_settings().demo_mode_enabled:
        raise HTTPException(status_code=404, detail="Demo mode disabled")
    return HTMLResponse(DEMO_HTML)


def _preview_messages(event: JobCompletedEvent, sentiment: Sentiment, outcome: ReviewOutcome) -> list[dict]:
    settings = get_settings()
    if outcome == ReviewOutcome.REVIEW_REQUEST_SENT:
        label = "Happy customer review SMS" if sentiment == Sentiment.POSITIVE else "Neutral customer review SMS"
        return [{"label": label, "to": event.customer_phone, "body": review_request_sms(event, sentiment)}]
    if outcome == ReviewOutcome.FEEDBACK_REQUEST_SENT:
        return [
            {"label": "Customer feedback SMS", "to": event.customer_phone, "body": negative_feedback_sms(event)},
            {"label": "Owner alert preview", "to": settings.demo_owner_phone_number, "body": owner_alert_sms(event, sentiment.value)},
        ]
    return []


async def demo_trigger(request: Request) -> dict:
    settings = get_settings()
    if not settings.demo_mode_enabled:
        raise HTTPException(status_code=404, detail="Demo mode disabled")
    if not settings.sms_dry_run and request.headers.get("X-LeadPilot-Key", "") != settings.manual_trigger_api_key:
        raise HTTPException(status_code=403, detail="Live SMS demo requires X-LeadPilot-Key")
    payload = await request.json()
    payload.setdefault("job_id", f"demo-{uuid4()}")
    demo_sentiment = payload.pop("demo_sentiment", None)
    sentiment_override = Sentiment(demo_sentiment) if demo_sentiment else None
    event = JobCompletedEvent.model_validate(payload)
    event.provider = "demo"
    event.customer_phone = normalize_phone(event.customer_phone)
    result = await handle_job_completed(event, sentiment_override=sentiment_override)
    sentiment = Sentiment(result["sentiment"]) if "sentiment" in result else Sentiment.NEUTRAL
    outcome = ReviewOutcome(result["outcome"])
    return {
        "demo_mode": True,
        "sms_mode": "dry_run" if settings.sms_dry_run else "live",
        "result": result,
        "sms_preview": _preview_messages(event, sentiment, outcome),
        "note": "Jobber, Housecall Pro, and GBP are production configuration points; this demo uses the manual completed-job trigger.",
    }
