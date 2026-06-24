-- ============================================================================
-- job_results — durable per-job result store (REVIEW + APPLY)
--
-- WHY THIS EXISTS
-- The backend keeps live jobs in an in-memory dict (jobs_store) that is wiped on
-- every Render restart / spin-down. The portal's full job result (executive
-- snapshot, contacts, signals, news, cost, etc.) only lived there and in
-- seller_jobs.result_data — and seller_jobs is written by a FRONTEND poller, so
-- it was only populated for seller-attributed jobs and only if a tab was open at
-- completion. Result: reloading the Job View after a restart showed an empty
-- dashboard.
--
-- This table is written SERVER-SIDE at job completion (persist_job_result in
-- production_main.py) for EVERY job, keyed by job_id, so a portal reload can
-- always recover the view via /job-result/{job_id} or a direct Supabase read.
--
-- ALL ADDITIVE: no existing table is altered or dropped.
-- Apply via the Supabase SQL editor AFTER review.
-- ============================================================================

create table if not exists job_results (
    job_id       text primary key,
    company_name text,
    status       text not null default 'completed',  -- completed | failed
    result       jsonb,
    updated_at   timestamptz not null default now()
);

comment on table job_results is
    'Durable per-job result store keyed by job_id. Written server-side at job completion so the portal recovers a job on reload after the in-memory jobs_store is wiped by a Render restart.';

-- Match the repo convention (001_sellers_and_seller_jobs.sql): RLS on + an
-- allow-all policy, so the backend (anon or service-role SUPABASE_KEY) and the
-- frontend supabase-js client can both read/write without being silently blocked.
alter table job_results enable row level security;
create policy "Allow all on job_results" on job_results
    for all using (true) with check (true);
