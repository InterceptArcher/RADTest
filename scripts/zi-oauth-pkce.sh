#!/usr/bin/env bash
#
# PKCE OAuth2 authorization_code -> token exchange for ZoomInfo (Okta).
#
# Use this INSTEAD of zi-oauth-exchange.sh when Okta rejects the exchange with:
#   "PKCE code verifier is required by the application."
#
# The ZoomInfo Okta app mandates PKCE (S256). This script:
#   1. Generates a code_verifier + code_challenge pair (kept in memory only).
#   2. Prints the login URL (with the code_challenge baked in) for you to open.
#   3. Waits for you to paste the authorization code from the callback page.
#   4. Exchanges the code for tokens, sending the matching code_verifier.
#
# Run it on your LAPTOP. The verifier must survive between the authorize step
# and the token step, which is why both halves live in ONE script run.
# Nothing is written to disk. Output goes to your terminal only.
#
# Usage:  bash scripts/zi-oauth-pkce.sh
#
set -euo pipefail

LOGIN_URL="https://login.zoominfo.com"
TOKEN_URL="https://okta-login.zoominfo.com/oauth2/default/v1/token"
REDIRECT_URI="https://radtest-backend-4mux.onrender.com/auth/zoominfo/callback"
SCOPES="openid offline_access"   # offline_access => Okta returns a refresh_token

command -v curl >/dev/null    || { echo "curl is required but not installed." >&2; exit 1; }
command -v python3 >/dev/null || { echo "python3 is required but not installed." >&2; exit 1; }

echo "ZoomInfo OAuth2 + PKCE token exchange"
echo "-------------------------------------"
echo "Redirect URI: ${REDIRECT_URI}"
echo

read -r  -p "ZOOMINFO_CLIENT_ID: "                ZI_CLIENT_ID
read -rs -p "ZOOMINFO_CLIENT_SECRET (hidden): "   ZI_CLIENT_SECRET
echo
echo

if [[ -z "${ZI_CLIENT_ID}" || -z "${ZI_CLIENT_SECRET}" ]]; then
  echo "ERROR: client_id and client_secret are both required." >&2
  exit 1
fi

# --- PKCE: generate verifier (32 random bytes, base64url) + S256 challenge ---
CODE_VERIFIER="$(python3 -c 'import secrets,base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode())')"
CODE_CHALLENGE="$(python3 -c 'import sys,hashlib,base64; print(base64.urlsafe_b64encode(hashlib.sha256(sys.argv[1].encode()).digest()).rstrip(b"=").decode())' "${CODE_VERIFIER}")"

# URL-encode the multi-word scope for the query string.
SCOPES_ENC="$(python3 -c 'import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))' "${SCOPES}")"

AUTH_LINK="${LOGIN_URL}/?client_id=${ZI_CLIENT_ID}&redirect_uri=${REDIRECT_URI}&response_type=code&scope=${SCOPES_ENC}&state=pkce&code_challenge=${CODE_CHALLENGE}&code_challenge_method=S256"

echo "STEP 1 — open this URL in your browser, log in, and copy the code from the callback page:"
echo
echo "${AUTH_LINK}"
echo
echo "(The code expires ~60s after it appears. Have this terminal ready.)"
echo
read -r -p "Authorization code: " ZI_AUTH_CODE
echo

if [[ -z "${ZI_AUTH_CODE}" ]]; then
  echo "ERROR: no authorization code entered." >&2
  exit 1
fi

echo "STEP 2 — exchanging code for tokens (with PKCE verifier)..."
echo

RESPONSE="$(curl -sS -X POST "${TOKEN_URL}" \
  -u "${ZI_CLIENT_ID}:${ZI_CLIENT_SECRET}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "grant_type=authorization_code" \
  --data-urlencode "code=${ZI_AUTH_CODE}" \
  --data-urlencode "redirect_uri=${REDIRECT_URI}" \
  --data-urlencode "code_verifier=${CODE_VERIFIER}")"

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
print("Paste these into Render -> radtest-backend -> Environment:")
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
        "WARNING: no refresh_token returned. The Okta app is missing the "
        "'offline_access' scope (or it isn't granted to this client), so Okta "
        "won't issue refresh tokens and you'll be back on the daily-expiry "
        "treadmill. Add 'offline_access' to the app's allowed scopes and re-run.",
        width=78,
    ))
PY

echo
echo "Done. Tokens were printed above only — nothing was saved to disk."
