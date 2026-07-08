create extension if not exists pgcrypto;

create table if not exists review_requests (
    id                  uuid primary key default gen_random_uuid(),
    business_id          text not null,
    customer_phone       text not null,
    customer_name        text not null,
    job_id               text not null,
    job_type             text not null,
    technician_name      text not null,
    sentiment            text not null,
    review_sms_sent      boolean not null default false,
    review_sms_sent_at   timestamptz,
    followup_sent        boolean not null default false,
    followup_sent_at     timestamptz,
    review_posted        boolean not null default false,
    outcome              text not null,
    created_at           timestamptz not null default now()
);

create index if not exists idx_review_requests_business_created
    on review_requests (business_id, created_at desc);

create index if not exists idx_review_requests_business_phone
    on review_requests (business_id, customer_phone, created_at desc);

create unique index if not exists idx_review_requests_business_job
    on review_requests (business_id, job_id);

create table if not exists review_suppressions (
    business_id text not null,
    phone       text not null,
    reason      text not null,
    created_at  timestamptz not null default now(),
    primary key (business_id, phone)
);
