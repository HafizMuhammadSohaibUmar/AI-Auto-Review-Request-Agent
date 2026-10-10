const fs = require('node:fs');
const path = require('node:path');
const out = __dirname;
const expr = (s) => `={{ ${s} }}`;
const body = (fn) => fn.toString().slice(fn.toString().indexOf('{') + 1, -1).trim();
const node = (name, type, version, parameters, x, y, extra = {}) => ({ id: name.toLowerCase().replace(/[^a-z0-9]+/g, '-'), name, type: `n8n-nodes-base.${type}`, typeVersion: version, parameters, position: [x, y], ...extra });
const link = (name, index = 0) => ({ node: name, type: 'main', index });

function normalizeEvent() {
  const p = $input.first().json.body ?? $input.first().json;
  const e = p.event ?? p.data ?? p;
  const phone = e.customer_phone ?? e.customer?.phone ?? e.client?.phones?.[0]?.number ?? e.phone;
  const name = e.customer_name ?? e.customer?.name ?? e.client?.name ?? e.name ?? 'Customer';
  const jobId = e.job_id ?? e.job?.id ?? e.id;
  if (!phone || !jobId) throw new Error('Completed-job webhook requires customer phone and job id');
  return [{ json: { business_id: 'REPLACE_WITH_BUSINESS_ID', job_id: String(jobId), customer_phone: phone, customer_name: name, job_type: e.job_type ?? e.service_type ?? e.title ?? 'home service', technician_name: e.technician_name ?? e.technician?.name ?? 'our technician', job_notes: e.job_notes ?? e.notes ?? e.summary ?? '', completed_at: e.completed_at ?? e.completedAt ?? new Date().toISOString(), received_at: new Date().toISOString() } }];
}

function dedupDecision() {
  const event = $('Normalize Completed Job').first().json;
  const rows = $input.all().map(i => i.json);
  const cutoff = Date.now() - 90 * 24 * 60 * 60 * 1000;
  const duplicate = rows.some(r => r.job_id === event.job_id || (r.customer_phone === event.customer_phone && Date.parse(r.created_at) >= cutoff));
  return [{ json: { ...event, duplicate } }];
}

function parseSentiment() {
  const event = $('Four-Hour Placeholder Guard').first().json;
  const raw = String($input.first().json.choices?.[0]?.message?.content ?? $input.first().json.output ?? '');
  const cleaned = raw.replace(/^```(?:json)?/i, '').replace(/```$/i, '').trim();
  let parsed;
  try { parsed = JSON.parse(cleaned); } catch { parsed = { sentiment: 'NEUTRAL', rationale: 'Mistral response was not valid JSON; safe neutral fallback used.' }; }
  const sentiment = ['POSITIVE', 'NEUTRAL', 'NEGATIVE'].includes(String(parsed.sentiment).toUpperCase()) ? String(parsed.sentiment).toUpperCase() : 'NEUTRAL';
  return [{ json: { ...event, sentiment, rationale: parsed.rationale ?? '' } }];
}

function followupGuard() {
  const row = $('Parse Sentiment').first().json;
  const reviews = $input.all().map(i => i.json);
  const name = String(row.customer_name).trim().toLowerCase();
  const sent = Date.parse(row.created_at ?? row.received_at);
  const found = reviews.some(r => String(r.reviewer?.displayName ?? r.reviewerDisplayName ?? '').trim().toLowerCase() === name && Date.parse(r.createTime ?? r.updateTime ?? 0) >= sent - 14 * 86400000);
  return [{ json: { ...row, review_detected: found } }];
}

const workflow = {
  id: 'ReviewRequestN8n20261010', name: 'AI Review Request - n8n Only (inactive until configured)', active: false,
  settings: { executionOrder: 'v1', timezone: 'America/New_York', errorWorkflow: '' }, staticData: null,
  nodes: [
    node('Credentials and Safety Notes', 'stickyNote', 1, { width: 700, height: 460, content: '## Credentials required before activation\nJobber webhook secret and/or Housecall Pro webhook secret; Supabase service-role credential; Mistral API credential for https://api.mistral.ai/v1/chat/completions; Twilio Account SID/Auth Token and approved SMS sender; Google Business Profile OAuth credential for review detection; owner E.164 number.\n\nValid JSON cannot contain comments, so this sticky note is the requested top-of-file credential block. Replace every REPLACE_WITH_* value. Verify Jobber/HCP HMAC signatures at ingress before production. Keep inactive until consent, STOP handling, SMS sender compliance, CRM webhook tests, and internal-number tests pass.' }, -520, -620),
    node('Job Completed Webhook', 'webhook', 1, { httpMethod: 'POST', path: 'review-request-job-completed-n8n', responseMode: 'onReceived', options: {} }, -380, -180),
    node('Normalize Completed Job', 'code', 2, { jsCode: body(normalizeEvent) }, -140, -180),
    node('90-Day Dedup (Supabase)', 'supabase', 1, { resource: 'row', operation: 'getAll', tableId: 'n8n_review_requests', returnAll: true, filters: { conditions: [{ keyName: 'customer_phone', condition: 'eq', keyValue: expr("$('Normalize Completed Job').first().json.customer_phone") }, { keyName: 'created_at', condition: 'gte', keyValue: expr('$now.minus({ days: 90 }).toISO()') }] }, options: {} }, 100, -180, { alwaysOutputData: true }),
    node('Four-Hour Placeholder Guard', 'code', 2, { jsCode: body(dedupDecision) }, 340, -180),
    node('Not Deduplicated?', 'if', 2, { conditions: { options: { typeValidation: 'strict' }, conditions: [{ leftValue: expr('$json.duplicate'), rightValue: false, operator: { type: 'boolean', operation: 'equal' } }] }, options: {} }, 560, -180),
    node('Classify Job Notes - Ministral 3B', 'httpRequest', 4.2, { method: 'POST', url: 'https://api.mistral.ai/v1/chat/completions', authentication: 'genericCredentialType', genericAuthType: 'httpHeaderAuth', sendBody: true, specifyBody: 'json', jsonBody: expr("JSON.stringify({model:'ministral-3b-latest',temperature:0,response_format:{type:'json_object'},messages:[{role:'system',content:'Classify home-service customer/job notes. Return JSON only: {sentiment: POSITIVE|NEUTRAL|NEGATIVE, rationale: short string}. NEGATIVE means complaint, unresolved issue, frustration, or explicit dissatisfaction. POSITIVE means clear satisfaction. Use NEUTRAL when unclear or uncertain.'},{role:'user',content:$json.job_notes}]})"), options: { timeout: 15000 } }, 800, -180),
    node('Parse Sentiment', 'code', 2, { jsCode: body(parseSentiment) }, 1040, -180),
    node('Negative Sentiment?', 'if', 2, { conditions: { options: { typeValidation: 'strict' }, conditions: [{ leftValue: expr('$json.sentiment'), rightValue: 'NEGATIVE', operator: { type: 'string', operation: 'equal' } }] }, options: {} }, 1260, -180),
    node('SMS Private Feedback', 'twilio', 1, { resource: 'sms', operation: 'send', from: 'REPLACE_WITH_TWILIO_E164', to: expr('$json.customer_phone'), message: expr("'Hi ' + $json.customer_name + ', thank you for letting us know. We are sorry the ' + $json.job_type + ' visit did not meet expectations. Please reply here with any details and our owner will review it. Reply STOP to opt out.'") }, 1500, -300),
    node('SMS Owner Negative Alert', 'twilio', 1, { resource: 'sms', operation: 'send', from: 'REPLACE_WITH_TWILIO_E164', to: 'REPLACE_WITH_OWNER_E164', message: expr("'NEGATIVE CUSTOMER FEEDBACK: ' + $json.customer_name + ' (' + $json.customer_phone + ') after ' + $json.job_type + '. Notes: ' + $json.job_notes") }, 1740, -300),
    node('SMS Google Review Request', 'twilio', 1, { resource: 'sms', operation: 'send', from: 'REPLACE_WITH_TWILIO_E164', to: expr('$json.customer_phone'), message: expr("'Hi ' + $json.customer_name + ', we hope everything is working well after your ' + $json.job_type + ' service. Would you mind leaving us a quick Google review? REPLACE_WITH_GOOGLE_REVIEW_URL - REPLACE_WITH_BUSINESS_NAME. Reply STOP to opt out.'") }, 1500, 60),
    node('Log Review Request', 'supabase', 1, { resource: 'row', operation: 'create', tableId: 'n8n_review_requests', dataToSend: 'defineBelow', fieldsUi: { fieldValues: [['business_id', expr('$json.business_id')], ['job_id', expr('$json.job_id')], ['customer_phone', expr('$json.customer_phone')], ['customer_name', expr('$json.customer_name')], ['job_type', expr('$json.job_type')], ['technician_name', expr('$json.technician_name')], ['sentiment', expr('$json.sentiment')], ['review_sms_sent', expr('$json.sentiment !== "NEGATIVE"')], ['review_posted', false], ['followup_sent', false], ['outcome', expr('$json.sentiment === "NEGATIVE" ? "feedback_request_sent" : "review_request_sent"')]].map(([fieldId, fieldValue]) => ({ fieldId, fieldValue })) } }, 1980, 60),
    node('Wait 48 Hours', 'wait', 1.1, { resume: 'timeInterval', amount: 48, unit: 'hours' }, 2200, 60),
    node('Due Follow-up Row (Supabase)', 'supabase', 1, { resource: 'row', operation: 'getAll', tableId: 'n8n_review_requests', returnAll: true, filters: { conditions: [{ keyName: 'job_id', condition: 'eq', keyValue: expr("$('Parse Sentiment').first().json.job_id") }, { keyName: 'followup_sent', condition: 'eq', keyValue: false }, { keyName: 'review_posted', condition: 'eq', keyValue: false }] }, options: {} }, 2440, 60, { alwaysOutputData: true }),
    node('GBP Recent Reviews', 'httpRequest', 4.2, { method: 'GET', url: 'https://mybusiness.googleapis.com/v4/REPLACE_WITH_GBP_ACCOUNT_ID/locations/REPLACE_WITH_GBP_LOCATION_ID/reviews', authentication: 'predefinedCredentialType', nodeCredentialType: 'googleOAuth2Api', options: { timeout: 15000 } }, 2680, 60),
    node('Review Follow-up Guard', 'code', 2, { jsCode: body(followupGuard) }, 2920, 60),
    node('No Review and No Opt-Out?', 'if', 2, { conditions: { options: { typeValidation: 'strict' }, conditions: [{ leftValue: expr('$json.review_detected'), rightValue: false, operator: { type: 'boolean', operation: 'equal' } }] }, options: {} }, 3160, 60),
    node('SMS Review Follow-up', 'twilio', 1, { resource: 'sms', operation: 'send', from: 'REPLACE_WITH_TWILIO_E164', to: expr('$json.customer_phone'), message: expr("'Hi ' + $json.customer_name + ', just following up from ' + $json.job_type + '. If our team helped, we would appreciate a quick Google review: REPLACE_WITH_GOOGLE_REVIEW_URL. Reply STOP to opt out.'") }, 3400, 60),
    node('Mark Follow-up Sent', 'supabase', 1, { resource: 'row', operation: 'update', tableId: 'n8n_review_requests', dataToSend: 'defineBelow', fieldsUi: { fieldValues: [['followup_sent', true], ['followup_sent_at', expr('$now.toISO()')]].map(([fieldId, fieldValue]) => ({ fieldId, fieldValue })) }, filters: { conditions: [{ keyName: 'job_id', condition: 'eq', keyValue: expr("$('Parse Sentiment').first().json.job_id") }] } }, 3640, 60),
  ],
  connections: {
    'Job Completed Webhook': { main: [[link('Normalize Completed Job')]] }, 'Normalize Completed Job': { main: [[link('90-Day Dedup (Supabase)')]] },
    '90-Day Dedup (Supabase)': { main: [[link('Four-Hour Placeholder Guard')]] }, 'Four-Hour Placeholder Guard': { main: [[link('Not Deduplicated?')]] },
    'Not Deduplicated?': { main: [[link('Classify Job Notes - Ministral 3B')], []] }, 'Classify Job Notes - Ministral 3B': { main: [[link('Parse Sentiment')]] },
    'Parse Sentiment': { main: [[link('Negative Sentiment?')]] }, 'Negative Sentiment?': { main: [[link('SMS Private Feedback')], [link('SMS Google Review Request')]] },
    'SMS Private Feedback': { main: [[link('SMS Owner Negative Alert')]] }, 'SMS Owner Negative Alert': { main: [[link('Log Review Request')]] },
    'SMS Google Review Request': { main: [[link('Log Review Request')]] }, 'Log Review Request': { main: [[link('Wait 48 Hours')]] },
    'Wait 48 Hours': { main: [[link('Due Follow-up Row (Supabase)')]] }, 'Due Follow-up Row (Supabase)': { main: [[link('GBP Recent Reviews')]] },
    'GBP Recent Reviews': { main: [[link('Review Follow-up Guard')]] }, 'Review Follow-up Guard': { main: [[link('No Review and No Opt-Out?')]] },
    'No Review and No Opt-Out?': { main: [[link('SMS Review Follow-up')], []] }, 'SMS Review Follow-up': { main: [[link('Mark Follow-up Sent')]] },
  },
};

fs.writeFileSync(path.join(out, 'ai-review-request-n8n.json'), JSON.stringify(workflow, null, 2) + '\n');
