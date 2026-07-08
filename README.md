# LeadPilot AI Review Request Agent

AI-powered review request automation for home-service businesses.

This service listens for completed-job events, validates the source, classifies job notes for customer satisfaction, sends either a Google review request or a private feedback request, logs the workflow in Supabase, and sends one gentle follow-up after 48 hours when appropriate.

## LeadPilot AI Agent Suite

| # | Agent | Purpose | Status |
| --- | --- | --- | --- |
| 1 | LeadPilot AI Voice Agent | Inbound call qualification and emergency escalation. | Live |
| 2 | Missed Call Text-Back Agent | SMS recovery after missed calls. | Planned |
| 3 | Outbound Follow-Up Agent | Campaign follow-up automation. | Planned |
| 4 | AI Review Request Agent | Sentiment-aware review request automation. | This repo |
| 5 | Web Chat Lead Qualifier | RAG-powered website chat qualification. | Planned |

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

## Deployment

This service can run on the same DigitalOcean Droplet and Supabase project as the other LeadPilot AI agents.

Use a different port from Agent 1:

```bash
docker compose up --build -d
```

If using a reverse proxy, route this app as a separate subdomain or path, for example:

```text
reviews.leadpilotai.sohaib.systems
```

## Notes

- Suppressions are scoped by `business_id`, so the same Supabase project can safely host multiple businesses.
- The Google Business Profile review-detection API is implemented in `ReviewTracker`.
- This service uses the same Supabase project pattern as Agent 1, with separate tables and `business_id`.
