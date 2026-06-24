-- ============================================================================
-- ZoomInfo auth token persistence — additive migration (REVIEW + APPLY)
--
-- WHY THIS EXISTS
-- ZoomInfo's Okta OAuth2 refresh_token ROTATES on every use: each successful
-- refresh returns a brand-new refresh_token and invalidates the previous one
-- after a ~30s grace window. The backend (worker/zoominfo_client.py) already
-- handles this — it stores the rotated token and calls _persist_refresh_token()
-- to save it. BUT that persistence targets this `zi_auth_tokens` table, which
-- was never created by any migration. So every persist silently failed, and
-- after each Render cold start the backend reloaded the original (now-dead)
-- ZOOMINFO_REFRESH_TOKEN env seed, got a 401, and fell back to the static
-- 24h ZOOMINFO_ACCESS_TOKEN — which is why the token had to be replaced daily.
--
-- Creating this table makes the rotated refresh_token survive restarts, which
-- is the durable fix for the "ZoomInfo expires every day" problem.
--
-- ALL ADDITIVE: no existing table is altered or dropped.
-- Apply via the Supabase SQL editor AFTER review.
-- ============================================================================

create table if not exists zi_auth_tokens (
    id          text primary key,           -- e.g. 'zoominfo_refresh_token'
    token_value text not null,              -- the current (rotated) refresh_token
    updated_at  timestamptz not null default now()
);

comment on table zi_auth_tokens is
    'Single-row key/value store for the rotating ZoomInfo Okta refresh_token so it survives Render restarts. Written by worker/zoominfo_client.py _persist_refresh_token().';

-- The backend uses the service-role key, which bypasses RLS. We still enable RLS
-- with no public policy so the table is never exposed via the anon/public API.
alter table zi_auth_tokens enable row level security;
