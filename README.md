# LeadPilot AI Review Request Agent

AI-powered review request automation for home-service businesses.

This service listens for completed-job events, validates the source, classifies job notes for customer satisfaction, sends either a Google review request or a private feedback request, logs the workflow in Supabase, and sends one gentle follow-up after 48 hours when appropriate.

## Architecture

```text
Jobber / Housecall Pro / Manual Completed Job
  -> FastAPI webhook or manual trigger
  -> source signature/API-key validation
  -> phone normalization + STOP suppression + 90-day dedup
  -> LiteLLM/Ministral sentiment classification
  -> positive/neutral: Google review SMS
  -> negative: private feedback SMS + owner alert
  -> Supabase review_requests
  -> scheduled 48-hour follow-up check
```

## Engineering Points

- Completed-job events are routed through signature/API-key validation before any customer message is generated.
- Sentiment routing separates happy/neutral review requests from complaint-handling feedback flows.
- STOP suppression, 90-day deduplication, and one-follow-up limits are part of the workflow rather than afterthoughts.
- The Google Business Profile tracker is isolated behind a service boundary so the core workflow still runs when GBP credentials are not configured.
- The browser demo exercises the same routing and Supabase logging path without requiring live Jobber, Housecall Pro, or GBP accounts.

## Related AI Systems

| System | Purpose | Live Demo | Repository |
| --- | --- | --- | --- |
| LeadPilot AI Voice Agent | Inbound phone agent for call qualification, emergency detection, and lead logging. | [Live Demo](https://leadpilotai.sohaib.systems/) | [Repository](https://github.com/HafizMuhammadSohaibUmar/LeadPilotAI) |
| Missed Call Text-Back AI Agent | SMS recovery and qualification after no-answer or busy calls. | [Live Demo](https://missed-call-text-back-ai-agent.sohaib.systems/demo) | [Repository](https://github.com/HafizMuhammadSohaibUmar/Missed-Call-Text-Back-AI-Agent) |
| Outbound Follow-Up AI Agent | Estimate, no-show, re-engagement, and seasonal follow-up campaigns. | [Live Demo](https://outbound-followup-ai-agent.sohaib.systems/demo) | [Repository](https://github.com/HafizMuhammadSohaibUmar/Outbound-Follow-Up-AI-Agent) |
| AI Auto Review Request Agent | Sentiment-aware post-job review and private feedback routing. | [Live Demo](https://ai-review-agent.sohaib.systems/demo) | **This repo** |
| Web Chat Lead Qualifier Agent | Embeddable RAG chat widget for contractor websites. | [Live Demo](https://web-chat-lead-qualifier-agent.sohaib.systems/demo) | [Repository](https://github.com/HafizMuhammadSohaibUmar/Web-Chat-Lead-Qualifier-Agent) |
| Personal AI Agent | Self-hosted task, planning, and local-calendar assistant with LangGraph tools. | [Live Demo](https://personal-ai-agent.sohaib.systems/) | [Repository](https://github.com/HafizMuhammadSohaibUmar/Personal-AI-Agent) |
| Invoxia AI for ERPNext | Frappe/ERPNext assistant layer for navigation, voice input foundations, and live ERP answers. | [Live Demo](https://invoxia.sohaib.systems/) | [Repository](https://github.com/HafizMuhammadSohaibUmar/InvoxiaAI-ERPNext) |

## Core Flow

1. Receive a completed-job webhook.
2. Validate the webhook signature.
3. Normalize customer phone to E.164.
4. Skip suppressed numbers.
5. Skip customers who received a review request in the last 90 days.
6. Classify job notes as `POSITIVE`, `NEUTRAL`, or `NEGATIVE`.
7. Send Google review SMS for positive or neutral jobs.
8. Send private feedback SMS and owner alert for negative jobs.
9. Store the request in Supabase.
10. Send one 48-hour follow-up if no review is detected and the customer has not opted out.

## Routes

| Route | Purpose |
| --- | --- |
| `POST /webhook/job-completed/jobber` | Jobber completed-job webhook with HMAC validation |
| `POST /webhook/job-completed/housecallpro` | Housecall Pro completed-job webhook with HMAC validation |
| `POST /webhook/job-completed` | Generic JSON webhook with `X-LeadPilot-Signature` HMAC validation |
| `POST /manual-trigger` | Manual test trigger protected by `X-LeadPilot-Key` |
| `GET /demo` | Browser demo for completed-job scenarios |
| `POST /demo/trigger` | Demo trigger; dry-run SMS by default |
| `POST /sms/reply` | Twilio inbound SMS reply webhook for STOP handling |
| `POST /followup/run` | Manual follow-up runner |
| `GET /metrics` | 7-day review request metrics |
| `GET /health` | Sentiment, Supabase, and Twilio health |

## Local Setup

```bash
cp .env.example .env
pip install -r requirements.txt
uvicorn main:app --port 8004
```

Run the Supabase migration:

```text
db/migrations/001_init.sql
```

## Webhook Security

The provider webhook routes fail closed if their secrets are missing. Configure:

```text
JOBBER_WEBHOOK_SECRET=...
HOUSECALLPRO_WEBHOOK_SECRET=...
INTERNAL_WEBHOOK_SECRET=...
MANUAL_TRIGGER_API_KEY=...
```

The generic webhook signs the raw JSON request body with HMAC SHA-256 and sends it in:

```text
X-LeadPilot-Signature: <hex digest>
```

Manual tests call `/manual-trigger` with:

```text
X-LeadPilot-Key: <MANUAL_TRIGGER_API_KEY>
```

## Live Demo Without Vendor Accounts

The service includes a browser demo at:

```text
https://ai-review-agent.sohaib.systems/demo
```

The demo uses the same completed-job workflow as production: phone normalization, suppression checks, 90-day deduplication, sentiment classification, routing, Supabase logging, and metrics. It does not require a Jobber account, Housecall Pro account, or verified Google Business Profile.


In dry-run mode, the app shows the exact SMS that would be sent without sending through Twilio. For live SMS demos, set `SMS_DRY_RUN=false`; `/demo/trigger` then requires `X-LeadPilot-Key` to avoid unauthenticated SMS sends.

Complaint scenarios show two separate preview cards: the customer feedback SMS and the owner alert. The owner alert preview uses `DEMO_OWNER_PHONE_NUMBER` so a public demo never exposes a real owner number.

## Google Review Tracking

Review links use:

```text
https://search.google.com/local/writereview?placeid={GBP_PLACE_ID}
```

Follow-up review detection uses the Google Business Profile reviews API when these are configured:

```text
GBP_ACCOUNT_ID=...
GBP_LOCATION_ID=...
GBP_ACCESS_TOKEN=...
```

Google reviews do not expose the original job id or customer phone, so the tracker matches recent GBP reviews by customer display name after the review request time. If GBP credentials are not configured, review tracking reports `configured: false` in `/health` and follow-ups continue based on Supabase state and STOP suppressions.

## Testing

```bash
pytest tests/ -v
```

## Notes

- Suppressions are scoped by `business_id`, so the same Supabase project can safely host multiple businesses.
- The Google Business Profile review-detection API is implemented in `ReviewTracker`.
- This service uses the same Supabase project pattern as [LeadPilotAI Agent](https://github.com/HafizMuhammadSohaibUmar/LeadPilotAI), with separate tables and `business_id`.

