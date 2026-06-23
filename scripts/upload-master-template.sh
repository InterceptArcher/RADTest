#!/usr/bin/env bash
# Create the public `decks` Storage bucket (if missing) and upload the master
# .pptx template to Supabase Storage. CI-safe, non-interactive, env-only creds.
#
# Usage:
#   export SUPABASE_URL="https://<ref>.supabase.co"
#   export SUPABASE_SERVICE_KEY="<service_role_key>"   # Settings -> API -> service_role
#   ./scripts/upload-master-template.sh "template /Account-Intelligence-Report Template for Claude to follow.pptx"
#
# The renderer reads SUPABASE_STORAGE_BUCKET_DECKS (default: decks) and the key
# master-template.pptx.
set -euo pipefail

TEMPLATE_PATH="${1:?Usage: upload-master-template.sh <path-to-master.pptx>}"
BUCKET="${SUPABASE_STORAGE_BUCKET_DECKS:-decks}"
KEY="master-template.pptx"

: "${SUPABASE_URL:?SUPABASE_URL must be set}"
: "${SUPABASE_SERVICE_KEY:?SUPABASE_SERVICE_KEY must be set (service_role key)}"
[[ -f "$TEMPLATE_PATH" ]] || { echo "ERROR: template not found: $TEMPLATE_PATH" >&2; exit 1; }

auth=(-H "Authorization: Bearer ${SUPABASE_SERVICE_KEY}")

echo "Ensuring bucket '${BUCKET}' exists (public)…"
# Idempotent: ignore 'already exists' conflict.
curl -fsS "${auth[@]}" -H "Content-Type: application/json" \
  -X POST "${SUPABASE_URL}/storage/v1/bucket" \
  -d "{\"name\":\"${BUCKET}\",\"public\":true}" >/dev/null 2>&1 || true

echo "Uploading $(basename "$TEMPLATE_PATH") -> ${BUCKET}/${KEY}…"
curl -fsS "${auth[@]}" \
  -H "Content-Type: application/vnd.openxmlformats-officedocument.presentationml.presentation" \
  -H "x-upsert: true" \
  -X POST "${SUPABASE_URL}/storage/v1/object/${BUCKET}/${KEY}" \
  --data-binary "@${TEMPLATE_PATH}" >/dev/null

echo "Uploaded. Public URL:"
echo "  ${SUPABASE_URL}/storage/v1/object/public/${BUCKET}/${KEY}"
