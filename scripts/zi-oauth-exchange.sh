#!/usr/bin/env bash
#
# One-shot OAuth2 authorization_code → token exchange for ZoomInfo (Okta).
#
# Run this on your LAPTOP right after capturing the auth code from
# the /auth/zoominfo/callback page in your browser. The code expires in
# ~60 seconds, so have the values ready before you start.
#
# All inputs are read from stdin (CLIENT_SECRET is hidden). Nothing is
# written to disk. Output goes to your terminal only.
#
# Usage:  bash scripts/zi-oauth-exchange.sh
#

set -euo pipefail

TOKEN_URL="https://okta-login.zoominfo.com/oauth2/default/v1/token"
REDIRECT_URI="https://radtest-backend-4mux.onrender.com/auth/zoominfo/callback"

command -v curl >/dev/null   || { echo "curl is required but not installed." >&2; exit 1; }
command -v python3 >/dev/null || { echo "python3 is required but not installed." >&2; exit 1; }

echo "ZoomInfo OAuth2 token exchange"
echo "------------------------------"
echo "Redirect URI: ${REDIRECT_URI}"
echo

read -r  -p  "ZOOMINFO_CLIENT_ID: "          ZI_CLIENT_ID
read -rs -p  "ZOOMINFO_CLIENT_SECRET (hidden): " ZI_CLIENT_SECRET
echo
read -r  -p  "Authorization code (expires ~60s): " ZI_AUTH_CODE
echo

if [[ -z "${ZI_CLIENT_ID}" || -z "${ZI_CLIENT_SECRET}" || -z "${ZI_AUTH_CODE}" ]]; then
  echo "ERROR: client_id, client_secret, and auth code are all required." >&2
  exit 1
fi

echo "Exchanging code for tokens..."
echo

RESPONSE="$(curl -sS -X POST "${TOKEN_URL}" \
  -u "${ZI_CLIENT_ID}:${ZI_CLIENT_SECRET}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "grant_type=authorization_code" \
  --data-urlencode "code=${ZI_AUTH_CODE}" \
  --data-urlencode "redirect_uri=${REDIRECT_URI}")"

# Parse and print results without ever leaving the local machine.
python3 - "${RESPONSE}" <<'PY'
import json, sys, textwrap

raw = sys.argv[1]
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    print("ERROR: Okta did not return JSON. Raw response:", file=sys.stderr)
    print(raw, file=sys.stderr)
    sys.exit(1)

if "access_token" not in data:
    print("ERROR: Okta returned a non-success response:", file=sys.stderr)
    print(json.dumps(data, indent=2), file=sys.stderr)
    sys.exit(1)

access_token  = data["access_token"]
refresh_token = data.get("refresh_token", "")
expires_in    = data.get("expires_in", "?")
scope         = data.get("scope", "?")

print("SUCCESS")
print()
print("Paste these into Render → radtest-backend-4mux → Environment:")
print()
print(f"  ZOOMINFO_ACCESS_TOKEN  = {access_token}")
print(f"  ZOOMINFO_REFRESH_TOKEN = {refresh_token}" if refresh_token else
      "  ZOOMINFO_REFRESH_TOKEN = (none returned — see warning below)")
print()
print(f"access_token expires in: {expires_in}s")
print(f"granted scopes:          {scope}")

if not refresh_token:
    print()
    print(textwrap.fill(
        "WARNING: no refresh_token in the response. The Okta app for "
        "RADTest does not have the 'offline_access' scope enabled, so "
        "Okta won't issue refresh tokens. The access_token alone is good "
        "for ~24h but won't auto-refresh. Add 'offline_access' to the "
        "Okta app's allowed scopes and re-run the flow.",
        width=78,
    ))
PY

echo
echo "Done. Tokens were printed above only — nothing was saved to disk."
