#!/usr/bin/env bash
# Apply the v3.1 additive migration to Supabase Postgres.
# CI-safe, non-interactive, reads credentials from the environment only.
#
# Usage:
#   export SUPABASE_DB_URL="postgresql://postgres:<pw>@db.<ref>.supabase.co:5432/postgres"
#   ./scripts/apply-migration.sh
#
# Get SUPABASE_DB_URL from: Supabase Dashboard -> Project Settings -> Database ->
# Connection string (URI). Do NOT commit it; export it in your shell.
set -euo pipefail

MIGRATION="$(dirname "$0")/../backend/migrations/2026-06-23_v3_1_pipeline.sql"

if [[ -z "${SUPABASE_DB_URL:-}" ]]; then
  echo "ERROR: SUPABASE_DB_URL must be set (Postgres connection URI). Not printing it." >&2
  exit 1
fi
if [[ ! -f "$MIGRATION" ]]; then
  echo "ERROR: migration file not found: $MIGRATION" >&2
  exit 1
fi
if ! command -v psql >/dev/null 2>&1; then
  echo "ERROR: psql not found. Install postgresql-client, or paste the SQL into the Supabase SQL editor instead." >&2
  exit 1
fi

echo "Applying migration: $(basename "$MIGRATION")"
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f "$MIGRATION"
echo "Migration applied. (All statements are CREATE TABLE IF NOT EXISTS — safe to re-run.)"
