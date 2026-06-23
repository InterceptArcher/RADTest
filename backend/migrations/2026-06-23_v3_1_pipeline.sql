-- ============================================================================
-- RAD Pipeline v3.1 — additive migration (REVIEW ONLY — do not auto-apply)
--
-- Creates the central per-job table (replaces the in-memory jobs_store so every
-- job — regardless of seller — is persisted to Supabase with its full debug
-- trail) plus the two resolution/enrichment cache tables. ALL ADDITIVE: no
-- existing table is altered or dropped. The legacy `slideshow_status` referenced
-- in the design doc does not exist in this codebase, so there is nothing to drop.
--
-- Apply via the Supabase SQL editor / migration tooling AFTER review.
-- ============================================================================

-- Central job store ----------------------------------------------------------
create table if not exists profile_requests (
    id                  uuid primary key default gen_random_uuid(),
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),

    -- request inputs
    input_name          text not null,
    salesperson_name    text,
    canada_only         boolean not null default false,

    -- lifecycle / live progress
    status              text not null default 'queued',  -- queued|processing|done|failed
    current_stage       text,        -- 1_resolution|2_general|3_contacts|4_council|5_format|6_render|done|failed
    current_step        text,
    current_stage_seq   integer not null default 0,       -- monotonic out-of-order guard
    step_progress       numeric(3,2) not null default 0,  -- 0.0–1.0 within current step

    -- accumulating outputs
    partial_results     jsonb not null default '{}'::jsonb,
    contact_catalogue   jsonb not null default '{}'::jsonb,  -- 6 persona buckets, all examined
    slide_contacts      jsonb not null default '{}'::jsonb,  -- selected (variable N >= 4)
    enrichment_trace    jsonb not null default '[]'::jsonb,
    data_quality_score  numeric(3,2),
    warnings            jsonb not null default '[]'::jsonb,
    debug_logs          jsonb not null default '[]'::jsonb,  -- JobLogger entries (PII-redacted)

    -- final artifact
    slideshow_url       text,
    error_code          text,
    error_message       text
);

create index if not exists profile_requests_status_idx     on profile_requests (status);
create index if not exists profile_requests_created_at_idx  on profile_requests (created_at desc);

-- Claude resolution cache (Stage 1) ------------------------------------------
create table if not exists claude_resolution_cache (
    cache_key          text primary key,        -- normalize(input_name) | primary_domain
    canonical_company  jsonb not null,
    decision_basis     text,
    created_at         timestamptz not null default now(),  -- TTL anchor (30d)
    last_hit_at        timestamptz
);

-- LinkedIn enrichment cache (Stage 3) ----------------------------------------
create table if not exists linkedin_enrichment_cache (
    linkedin_url  text primary key,
    enrichment    jsonb not null,   -- {start_date, current_position_confirmed, extracted_snippet, source_url}
    created_at    timestamptz not null default now()  -- TTL anchor (7d)
);

-- Storage bucket for rendered decks (create via Supabase Storage; shown for ref):
--   bucket: decks   (public read)   -> SUPABASE_STORAGE_BUCKET_DECKS
