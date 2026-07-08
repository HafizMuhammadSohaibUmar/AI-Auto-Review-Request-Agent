# Decisions

This service is Agent 4 in the LeadPilot AI Agent Suite: the AI Review Request Agent for home-service businesses.

## Product Boundary

The agent only acts after a completed job. It does not qualify leads, answer calls, or run marketing campaigns. Its job is to turn satisfied completed-service customers into Google review requests while routing unhappy customers into private feedback before a public review request is sent.

## Runtime

FastAPI and Uvicorn are used because the workflow is webhook-first: Jobber, Housecall Pro, Twilio inbound SMS, manual triggers, metrics, and follow-up runs are all simple HTTP surfaces.

The service is designed to run on the same DigitalOcean Droplet as Agent 1, but on a different port (`8004`) and with a separate repository. This keeps deployment cost low while preserving independent code ownership and release history for each agent.

## Data Storage

The same Supabase project can be reused, but this agent owns separate tables:

- `review_requests`
- `review_suppressions`

Rows include `business_id` so the same database pattern can support multiple businesses later without changing the handler contract.

## Sentiment Model

The sentiment task is intentionally small: classify a job note as `POSITIVE`, `NEUTRAL`, or `NEGATIVE`. A large model would add cost and latency without meaningful value, so the service uses Mistral's small Ministral model through LiteLLM.

The configured model is `mistral/ministral-3b-latest`. This replaces the originally written `mistral/open-ministral-3b` name because the earlier health check showed that model id is invalid with the Mistral API.

If sentiment classification fails, the handler defaults to `NEUTRAL`. That sends a normal review request instead of blocking the workflow. Negative routing still happens when the model explicitly returns `NEGATIVE`.

## Webhook Security

Jobber and Housecall Pro payloads are validated with HMAC SHA-256 signatures before parsing. Each provider has a separate secret and configurable signature header so one integration can be rotated or adjusted without changing the other.

The generic `/webhook/job-completed` endpoint is also protected with an internal HMAC secret. `/manual-trigger` is protected by an API key header. This keeps demo and test surfaces useful without leaving unauthenticated production write paths open.

Twilio inbound SMS signatures are also validated by default for `/sms/reply`. Local testing can disable this with `VALIDATE_TWILIO_SIGNATURE=false`.

## Phone Handling

Customer numbers are normalized to E.164 before suppression checks, dedup checks, logging, and SMS sending. The default country is US because the target home-service market and Twilio setup are US-first.

## Deduplication

The service skips customers who already received a review request within the previous 90 days. This avoids repeat asks, lowers opt-out risk, and keeps the agent aligned with a normal local-business review cadence.

## Negative Job Routing

Negative notes do not receive a Google review request. The customer receives a private feedback SMS and the owner receives an alert. This protects the business while still creating a fast recovery path.

## Follow-Up

Each job can receive at most one follow-up, after 48 hours. Follow-ups are skipped when:

- the number has opted out with STOP
- the request was already followed up
- a review is detected for the job

`ReviewTracker` calls the Google Business Profile reviews API when `GBP_ACCOUNT_ID`, `GBP_LOCATION_ID`, and `GBP_ACCESS_TOKEN` are configured. The official GBP reviews list endpoint returns reviews for a verified location, but reviews do not include the FSM job id or customer phone. The tracker therefore matches by customer display name and review timing after the review request.

If GBP OAuth credentials are not configured, the service reports `configured: false` in `/health`. That is acceptable for local demos, but a live deployment should configure GBP OAuth to satisfy the no-review follow-up requirement.

## Testing Strategy

The tests focus on the branches that change user-visible behavior:

- positive sentiment sends a Google review request
- neutral sentiment sends a Google review request
- negative sentiment sends private feedback and an owner alert
- 90-day dedup skips SMS
- follow-up sends only when due and not suppressed
- follow-up skips when GBP review detection finds a matching customer review
- generic and manual trigger endpoints reject invalid credentials
