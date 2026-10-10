create table if not exists n8n_review_requests (
  id bigint generated always as identity primary key,
  business_id text not null,
  job_id text not null,
  customer_phone text not null,
  customer_name text not null,
  job_type text not null,
  technician_name text,
  sentiment text not null,
  review_sms_sent boolean not null default false,
  review_sms_sent_at timestamptz,
  followup_sent boolean not null default false,
  followup_sent_at timestamptz,
  review_posted boolean not null default false,
  outcome text not null,
  created_at timestamptz not null default now()
);
create unique index if not exists n8n_review_requests_business_job on n8n_review_requests (business_id, job_id);
create index if not exists n8n_review_requests_business_phone_created on n8n_review_requests (business_id, customer_phone, created_at desc);
