# AI Review Request Agent: n8n-only version

This is a separate n8n implementation of the existing review-request agent. It does not change the custom backend.

Import `ai-review-request-n8n.json`; it is inactive by default. Run `schema.sql` in the intended Supabase project first.

Webhook URL for Jobber or Housecall Pro:

`POST https://YOUR_N8N_DOMAIN/webhook/review-request-job-completed-n8n`

Configure the source FSM to send a completed-job payload containing a job id, customer phone/name, job type, technician, and job notes. Validate Jobber/HCP signatures at the ingress proxy or through an n8n signature-verification step before enabling production traffic.

The Mistral node calls `https://api.mistral.ai/v1/chat/completions` with `ministral-3b-latest` and expects JSON containing `sentiment` and `rationale`. Configure an n8n HTTP Header Auth credential with the Mistral bearer token.

Positive and neutral jobs receive the Google-review SMS. Negative jobs receive private feedback and an owner alert, but no Google-review request. Every request is deduplicated for 90 days. After 48 hours, the workflow checks the configured Google Business Profile reviews endpoint and sends one follow-up only when no matching review is detected and the request has not been marked complete or suppressed.

Use `REPLACE_WITH_*` search before activation. Test with internal numbers and `SMS_DRY_RUN`/Twilio test credentials where available.

Validate locally:

```powershell
node build-workflow.js
node test-workflow.js
```
