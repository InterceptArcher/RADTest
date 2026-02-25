"""
ZoomInfo API client for company enrichment, contact search,
intent signals, scoops, news, and technology data.

Supports two authentication modes:
1. Auto-auth (preferred): Provide client_id + client_secret for automatic
   token refresh via OAuth2 client_credentials grant.
2. Static token: Provide access_token directly (expires, no auto-refresh).

All credentials must be provided via environment variables.
"""
import asyncio
import base64
import logging
import os
import re
import time
from typing import Dict, Any, List, Optional

import httpx

logger = logging.getLogger(__name__)

ZOOMINFO_BASE_URL = "https://api.zoominfo.com"
ZOOMINFO_TOKEN_URL = "https://okta-login.zoominfo.com/oauth2/default/v1/token"

# ZoomInfo GTM API v1 endpoint paths.
# The GTM API uses /gtm/data/v1/ prefix with JSON:API request/response format.
# The old flat endpoints (/enrich/company, /search/contact, etc.) are legacy and
# return incorrect or missing data for many field types.
ENDPOINTS = {
    "company_enrich": "/gtm/data/v1/companies/enrich",
    "contact_search": "/gtm/data/v1/contacts/search",
    "contact_enrich": "/gtm/data/v1/contacts/enrich",
    "intent_enrich": "/gtm/data/v1/intent/enrich",
    "scoops_enrich": "/gtm/data/v1/scoops/enrich",
    "news_enrich": "/gtm/data/v1/news/enrich",
    "tech_enrich": "/gtm/data/v1/companies/technologies/enrich",
    # Legacy keys kept for backward compatibility (point to enrich endpoints)
    "scoops_search": "/gtm/data/v1/scoops/enrich",
    "news_search": "/gtm/data/v1/news/enrich",
}

# Fields explicitly requested from ZoomInfo contact search so that phone data
# is returned directly from the search step without a separate enrich call.
# Field names match ZoomInfo GTM API output field naming conventions.
OUTPUT_FIELDS = [
    "id",                   # ZoomInfo contact unique identifier (not personId)
    "firstName",
    "lastName",
    "email",
    "jobTitle",
    "managementLevel",
    "department",
    "linkedinUrl",          # ZoomInfo uses lowercase 'in' (linkedin not linkedIn)
    "phone",
    "directPhone",
    "mobilePhone",
    "companyPhone",
    "contactAccuracyScore",
]

# Required output fields for ZoomInfo company enrich requests.
# The GTM API /gtm/data/v1/companies/enrich endpoint accepts outputFields inside
# the JSON:API attributes.  Field names use camelCase per the GTM API schema.
# Fields not supported by a given subscription tier are silently omitted from the
# response rather than causing an error.
COMPANY_OUTPUT_FIELDS = [
    "id",
    "name",
    "website",
    "revenue",
    "revenueRange",
    "employeeCount",
    "city",
    "state",
    "country",
    "phone",
    "ticker",
]

# Output fields for contact enrich — explicitly request phone number fields.
# The GTM contact search endpoint does NOT return phone/email data (per ZoomInfo docs:
# "The Search Contacts API does not return emails, phone numbers, or any other data
# that can be used to engage").  Phone data is ONLY returned by the enrich endpoint
# when outputFields are specified.
# DNC flags are included so we can surface them in the UI if needed — we do NOT
# filter out DNC-flagged numbers (the user has API access to this data).
CONTACT_ENRICH_OUTPUT_FIELDS = [
    "firstName",
    "lastName",
    "fullName",
    "email",
    "jobTitle",
    "managementLevel",
    "department",
    "linkedInUrl",
    "phone",
    "directPhone",
    "mobilePhone",
    "companyPhone",
    "hasDirectPhone",
    "hasMobilePhone",
    "hasCompanyPhone",
    "directPhoneDoNotCall",
    "mobilePhoneDoNotCall",
    "contactAccuracyScore",
    "personId",
]

# Priority C-Suite titles — CTO, CFO, CMO, CIO are searched first.
# These are Intercept's primary target personas.
PRIORITY_CSUITE_TITLES = [
    "Chief Technology Officer", "CTO",
    "Chief Financial Officer", "CFO",
    "Chief Marketing Officer", "CMO",
    "Chief Information Officer", "CIO",
]

# Other C-Suite titles searched after priority titles.
# Excludes CTO/CFO/CMO/CIO (already in PRIORITY_CSUITE_TITLES).
OTHER_CSUITE_TITLES = [
    "Chief Executive Officer", "CEO",
    "Chief Operating Officer", "COO",
    "Chief Revenue Officer", "CRO",
    "Chief Product Officer", "CPO",
    "Chief People Officer", "Chief HR Officer", "Chief Human Resources Officer", "CHRO",
    "Chief Legal Officer", "CLO", "General Counsel",
    "Chief Security Officer", "CSO",
    "Chief Data Officer", "CDO",
    "Chief Customer Officer", "CCO",
    "Chief Commercial Officer",
    "Chief Information Security Officer", "CISO",
    "Chief Compliance Officer",
    "Chief Strategy Officer",
    "Chief Transformation Officer",
]

# Full C-Suite + leadership list (priority + other + VP/Director) for backward compatibility.
CSUITE_JOB_TITLES = PRIORITY_CSUITE_TITLES + OTHER_CSUITE_TITLES + [
    "Vice President", "VP", "SVP", "EVP",
    "Director", "Senior Director",
]

# North America country names passed to ZoomInfo contact search where supported.
# Used as a soft filter — falls back to global search if geo returns 0 results.
NORTH_AMERICA_COUNTRIES = ["United States", "Canada", "Mexico"]

# Broad B2B intent topics used when querying ZoomInfo Intent Enrich.
# ZoomInfo requires at least 1 topic; this set covers the domains most
# relevant to enterprise technology buying decisions.
DEFAULT_INTENT_TOPICS = [
    "Cybersecurity",
    "Cloud Computing",
    "Artificial Intelligence",
    "Machine Learning",
    "Digital Transformation",
    "Data Analytics",
    "Enterprise Software",
    "Business Intelligence",
    "Network Security",
    "IT Security",
    "Cloud Migration",
    "Data Management",
]


class ZoomInfoRateLimiter:
    """Token-bucket rate limiter for ZoomInfo's 25 req/sec limit."""

    def __init__(self, max_per_second: int = 25):
        self.max_per_second = max_per_second
        self.tokens = float(max_per_second)
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(
                self.max_per_second,
                self.tokens + elapsed * self.max_per_second
            )
            self.last_refill = now

            if self.tokens >= 1:
                self.tokens -= 1
                return True

            wait_time = (1 - self.tokens) / self.max_per_second
            await asyncio.sleep(wait_time)
            self.tokens = 0
            self.last_refill = time.monotonic()
            return True


class ZoomInfoClient:
    """
    Client for ZoomInfo GTM API.

    Endpoints:
    - Company Enrich: firmographic data
    - Contact Search: executive/people data
    - Intent Enrich: buying intent signals
    - Scoops Search: business events (hires, funding, etc.)
    - News Search: company news articles
    - Technologies Enrich: installed tech stack
    """

    def __init__(
        self,
        access_token: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        refresh_token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        self._client_id = client_id or os.getenv("ZOOMINFO_CLIENT_ID")
        self._client_secret = client_secret or os.getenv("ZOOMINFO_CLIENT_SECRET")
        # Username/password for ZoomInfo legacy /authenticate endpoint.
        # WARNING: The legacy /authenticate JWT does NOT work with GTM API v1
        # endpoints.  Kept only as a last-resort diagnostic fallback.
        self._username = username or os.getenv("ZOOMINFO_USERNAME")
        self._password = password or os.getenv("ZOOMINFO_PASSWORD")
        # Static token — can be an OAuth2 bearer token from ZoomInfo docs page (24h).
        self._static_token = access_token or os.getenv("ZOOMINFO_ACCESS_TOKEN")
        # Okta refresh_token for OAuth2 refresh_token grant (GTM API compatible).
        self._refresh_token = refresh_token or os.getenv("ZOOMINFO_REFRESH_TOKEN")
        # Auto-auth: refresh_token + client creds enable automatic OAuth2 token refresh.
        # Priority: OAuth2 refresh_token > static token > legacy /authenticate (fallback).
        self._auto_auth = bool(
            (self._refresh_token and self._client_id and self._client_secret)
            or (self._username and self._password)
        )
        self._token_expires_at = 0.0

        if self._auto_auth:
            # Token will be fetched on first request via _authenticate().
            self.access_token = None
        else:
            # Static token only — use it directly; cannot auto-refresh.
            self.access_token = self._static_token
            if not self.access_token:
                raise ValueError(
                    "ZoomInfo credentials required for GTM API v1. Set one of:\n"
                    "  1. ZOOMINFO_CLIENT_ID + ZOOMINFO_CLIENT_SECRET + ZOOMINFO_REFRESH_TOKEN "
                    "(recommended — auto-refresh)\n"
                    "  2. ZOOMINFO_ACCESS_TOKEN (OAuth2 bearer token from ZoomInfo docs, 24h)\n"
                    "These values must be provided via environment variables."
                )

        self.base_url = ZOOMINFO_BASE_URL
        self.timeout = timeout
        self.max_retries = max_retries
        self.headers = {
            # GTM API v1 uses JSON:API format — Content-Type must be
            # application/vnd.api+json for all request payloads.
            "Content-Type": "application/vnd.api+json",
            "Accept": "application/vnd.api+json, application/json",
        }
        if self.access_token:
            self.headers["Authorization"] = f"Bearer {self.access_token}"
        self.rate_limiter = ZoomInfoRateLimiter()

    async def _authenticate(self) -> None:
        """
        Fetch a fresh ZoomInfo access token for the GTM API v1.

        Strategy order (GTM API requires OAuth2 tokens — legacy JWTs don't work):

        1. Okta OAuth2 refresh_token grant  →  RECOMMENDED for GTM API
           POST https://okta-login.zoominfo.com/oauth2/default/v1/token
           Requires: ZOOMINFO_CLIENT_ID + ZOOMINFO_CLIENT_SECRET + ZOOMINFO_REFRESH_TOKEN
           Returns: OAuth2 access_token (24h) + rotated refresh_token.
           The rotated refresh_token is stored in memory for subsequent refreshes.

        2. Static ZOOMINFO_ACCESS_TOKEN  →  manual OAuth2 bearer token (24h)
           Must be an OAuth2 token obtained from ZoomInfo docs page or OAuth2 flow.
           Legacy JWTs from /authenticate will NOT work.

        3. Legacy username/password → /authenticate  →  LAST RESORT / DIAGNOSTIC
           WARNING: This produces a legacy JWT that does NOT work with GTM API v1.
           Kept only to provide a clear error message pointing users to OAuth2.
        """
        last_error: Optional[str] = None

        # ------------------------------------------------------------------ #
        # Strategy 1: Okta OAuth2 refresh_token grant (GTM API compatible)   #
        # ------------------------------------------------------------------ #
        if self._refresh_token and self._client_id and self._client_secret:
            credentials = f"{self._client_id}:{self._client_secret}"
            basic_auth = base64.b64encode(credentials.encode()).decode()
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        ZOOMINFO_TOKEN_URL,
                        headers={
                            "Authorization": f"Basic {basic_auth}",
                            "Content-Type": "application/x-www-form-urlencoded",
                        },
                        data=f"grant_type=refresh_token&refresh_token={self._refresh_token}",
                    )
                    response.raise_for_status()
                    token_data = response.json()

                self.access_token = token_data["access_token"]
                # Refresh tokens rotate — store the new one for subsequent refreshes.
                # The old refresh_token is invalidated after 30s grace period.
                if "refresh_token" in token_data:
                    old_rt = self._refresh_token[:8] + "..." if self._refresh_token else "none"
                    self._refresh_token = token_data["refresh_token"]
                    new_rt = self._refresh_token[:8] + "..."
                    logger.info(
                        "ZoomInfo refresh_token rotated: %s → %s (old invalidated after 30s)",
                        old_rt, new_rt
                    )
                    # Persist to Supabase for restart resilience (best-effort)
                    await self._persist_refresh_token(self._refresh_token)

                # OAuth2 access tokens are valid for 24 hours
                expires_in = token_data.get("expires_in", 86400)
                self._token_expires_at = time.time() + expires_in - 300
                self.headers["Authorization"] = f"Bearer {self.access_token}"
                logger.info(
                    "ZoomInfo OAuth2 token obtained via refresh_token grant, "
                    "expires in %ds (%dh)",
                    expires_in, expires_in // 3600
                )
                return

            except httpx.HTTPStatusError as e:
                try:
                    err_body = e.response.json()
                except Exception:
                    err_body = e.response.text[:300]
                last_error = f"OAuth2 refresh_token grant failed: HTTP {e.response.status_code} — {err_body}"
                logger.error(
                    "ZoomInfo OAuth2 refresh_token grant failed: HTTP %s — %s. "
                    "The refresh_token may have been rotated and the stored value is stale. "
                    "Obtain a new refresh_token via ZoomInfo OAuth2 authorization_code flow.",
                    e.response.status_code, err_body
                )
            except Exception as e:
                last_error = f"OAuth2 refresh_token grant exception: {e}"
                logger.error("ZoomInfo OAuth2 refresh_token exception: %s", e)

        # ------------------------------------------------------------------ #
        # Strategy 2: static ZOOMINFO_ACCESS_TOKEN (must be OAuth2 token)    #
        # ------------------------------------------------------------------ #
        if self._static_token:
            logger.warning(
                "ZoomInfo OAuth2 auto-refresh unavailable (%s). "
                "Using static ZOOMINFO_ACCESS_TOKEN. This MUST be an OAuth2 bearer "
                "token (from ZoomInfo docs page or OAuth2 flow), NOT a legacy JWT "
                "from /authenticate. OAuth2 tokens are valid for 24h.",
                last_error or "no OAuth2 credentials configured"
            )
            self.access_token = self._static_token
            # OAuth2 bearer tokens from ZoomInfo are valid 24h
            self._token_expires_at = time.time() + 82800  # 23h (conservative)
            self.headers["Authorization"] = f"Bearer {self.access_token}"
            return

        # ------------------------------------------------------------------ #
        # Strategy 3: legacy /authenticate — DIAGNOSTIC ONLY                 #
        # ------------------------------------------------------------------ #
        if self._username and self._password:
            logger.warning(
                "ZoomInfo: Attempting legacy /authenticate as last resort. "
                "WARNING: The JWT from this endpoint does NOT work with GTM API v1 "
                "endpoints (/gtm/data/v1/*). You MUST set up OAuth2 credentials: "
                "ZOOMINFO_CLIENT_ID + ZOOMINFO_CLIENT_SECRET + ZOOMINFO_REFRESH_TOKEN."
            )
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/authenticate",
                        json={"username": self._username, "password": self._password},
                        headers={"Content-Type": "application/json"},
                    )
                    response.raise_for_status()
                    token_data = response.json()

                jwt = token_data.get("jwt") or token_data.get("access_token")
                if not jwt:
                    raise ValueError(f"No jwt in response: {list(token_data.keys())}")

                self.access_token = jwt
                self._token_expires_at = time.time() + 3600 - 300
                self.headers["Authorization"] = f"Bearer {self.access_token}"
                logger.warning(
                    "ZoomInfo legacy JWT obtained — this will cause HTTP 401 on "
                    "GTM API v1 endpoints. Set up OAuth2 credentials ASAP."
                )
                return

            except httpx.HTTPStatusError as e:
                last_error = f"legacy /authenticate failed: HTTP {e.response.status_code}"
                logger.warning("ZoomInfo legacy /authenticate failed: %s", e.response.status_code)
            except Exception as e:
                last_error = f"legacy /authenticate exception: {e}"
                logger.warning("ZoomInfo legacy /authenticate exception: %s", e)

        raise ValueError(
            "ZoomInfo authentication failed — no valid OAuth2 credentials.\n"
            "The GTM API v1 requires OAuth2 tokens. Set these environment variables:\n"
            "  ZOOMINFO_CLIENT_ID     — from ZoomInfo Okta app\n"
            "  ZOOMINFO_CLIENT_SECRET — from ZoomInfo Okta app\n"
            "  ZOOMINFO_REFRESH_TOKEN — from OAuth2 authorization_code flow\n"
            "Or set ZOOMINFO_ACCESS_TOKEN with an OAuth2 bearer token (24h validity).\n"
            f"Last error: {last_error}"
        )

    async def _persist_refresh_token(self, token: str) -> None:
        """
        Best-effort persistence of rotated refresh_token to Supabase.
        This allows the token to survive Render service restarts.
        If Supabase is not configured or the table doesn't exist, fails silently.
        """
        try:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            if not supabase_url or not supabase_key:
                logger.debug("Supabase not configured — refresh_token stored in memory only")
                return

            from supabase import create_client
            sb = create_client(supabase_url, supabase_key)
            sb.table("zi_auth_tokens").upsert({
                "id": "zoominfo_refresh_token",
                "token_value": token,
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }).execute()
            logger.info("ZoomInfo refresh_token persisted to Supabase zi_auth_tokens table")
        except Exception as e:
            # Non-fatal — token is still in memory, just won't survive restart
            logger.debug("Could not persist refresh_token to Supabase: %s", e)

    async def _load_persisted_refresh_token(self) -> Optional[str]:
        """
        Try to load the latest refresh_token from Supabase.
        Returns None if Supabase is not configured or table doesn't exist.
        """
        try:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            if not supabase_url or not supabase_key:
                return None

            from supabase import create_client
            sb = create_client(supabase_url, supabase_key)
            result = sb.table("zi_auth_tokens").select("token_value").eq(
                "id", "zoominfo_refresh_token"
            ).execute()
            if result.data and result.data[0].get("token_value"):
                logger.info("Loaded persisted refresh_token from Supabase")
                return result.data[0]["token_value"]
        except Exception as e:
            logger.debug("Could not load refresh_token from Supabase: %s", e)
        return None

    async def _ensure_valid_token(self) -> None:
        """Re-authenticate if the current token is expired or missing."""
        if self._auto_auth and (
            not self.access_token or time.time() >= self._token_expires_at
        ):
            # On first auth attempt (or after restart), try loading a persisted
            # refresh_token from Supabase — it may be newer than the env var.
            if not self.access_token and self._refresh_token:
                persisted = await self._load_persisted_refresh_token()
                if persisted and persisted != self._refresh_token:
                    logger.info(
                        "Using persisted refresh_token from Supabase "
                        "(newer than env var)"
                    )
                    self._refresh_token = persisted
            await self._authenticate()

    async def _make_request(
        self, endpoint: str, payload: Dict[str, Any], _is_retry: bool = False,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make an authenticated POST request to ZoomInfo API.
        On HTTP 401 (expired token), re-authenticates once and retries.
        """
        await self._ensure_valid_token()
        await self.rate_limiter.acquire()
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"ZoomInfo POST {url}")
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url, json=payload, headers=self.headers, params=params,
            )
            # On first 401, force token refresh and retry once
            if response.status_code == 401 and not _is_retry and self._auto_auth:
                logger.warning(
                    "ZoomInfo 401 on %s — token likely expired, re-authenticating and retrying",
                    endpoint
                )
                self._token_expires_at = 0  # Force re-auth
                await self._authenticate()
                return await self._make_request(endpoint, payload, _is_retry=True, params=params)

            if not response.is_success:
                # Capture and log the full response body so the root cause is visible
                try:
                    body = response.json()
                except Exception:
                    body = response.text[:500]
                logger.error(
                    f"ZoomInfo API error: {response.status_code} {response.reason_phrase} "
                    f"for {url} — body: {body}"
                )
                # Store error body on the response object so callers can surface it
                # in debug logs without re-reading the (already consumed) stream.
                try:
                    response._zi_error_body = body  # type: ignore[attr-defined]
                except Exception:
                    pass
                response.raise_for_status()
            # Handle 204 No Content (valid empty response)
            if response.status_code == 204 or not response.content:
                return {}
            return response.json()

    @staticmethod
    def _http_error_detail(e: "httpx.HTTPStatusError") -> str:
        """
        Extract a human-readable error detail from an httpx.HTTPStatusError.
        Includes the status code plus the response body ZoomInfo sent back,
        so callers can surface the exact reason (plan restriction, bad field,
        wrong endpoint, etc.) in debug logs without re-reading the stream.
        """
        code = e.response.status_code
        # Try the pre-captured body first (set by _make_request above)
        body = getattr(e.response, "_zi_error_body", None)
        if body is None:
            try:
                body = e.response.json()
            except Exception:
                body = e.response.text[:400]
        return f"HTTP {code}: {body}"

    async def _request_with_fallback(
        self,
        endpoint: str,
        flat_payload: Dict[str, Any],
        jsonapi_type: str,
    ) -> Dict[str, Any]:
        """
        Try flat JSON format first, then JSON:API wrapper as fallback.

        The ZoomInfo standard API (https://api.zoominfo.com) uses flat JSON.
        JSON:API ({"data": {"type": "...", "attributes": {...}}}) is tried as
        fallback for backward compatibility in case the endpoint still accepts it.

        Format errors (HTTP 400, 415, 422) trigger the fallback.
        Auth errors (401, 403) and not-found (404) are raised immediately.
        """
        jsonapi_payload = {"data": {"type": jsonapi_type, "attributes": flat_payload}}
        last_error: Optional[Exception] = None
        for payload in (flat_payload, jsonapi_payload):
            try:
                return await self._make_request(endpoint, payload)
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code in (400, 415, 422):
                    logger.debug(
                        "ZoomInfo %s: HTTP %s (likely wrong format), trying alternate",
                        endpoint, e.response.status_code
                    )
                    continue
                raise  # Auth errors, 404s — propagate immediately
        # Both formats failed with format errors
        raise last_error  # type: ignore[misc]

    @staticmethod
    def _unwrap_jsonapi(records: list) -> list:
        """Unwrap JSON:API records: {"attributes": {...}} → flat dict.

        GTM API v1 returns records like:
            {"id": "123", "type": "Contact", "attributes": {"firstName": "John", ...}}
        Downstream normalization expects flat dicts:
            {"firstName": "John", ...}
        If the record has an "attributes" dict, merge it with any top-level id/type.
        Non-JSON:API records (no "attributes" key) are returned as-is.
        """
        unwrapped = []
        for rec in records:
            if isinstance(rec, dict) and "attributes" in rec and isinstance(rec["attributes"], dict):
                flat = dict(rec["attributes"])
                # Preserve top-level id if present and not already in attributes
                if "id" in rec and "id" not in flat:
                    flat["id"] = rec["id"]
                unwrapped.append(flat)
            else:
                unwrapped.append(rec)
        return unwrapped

    def _extract_data_list(self, response: Dict[str, Any]) -> list:
        """
        Extract the data list from a ZoomInfo API response.
        Handles multiple response formats:
          - {"data": [...]}                 (standard list / JSON:API)
          - {"data": {...}}                 (single-object — wrapped in list)
          - {"result": {"data": [...]}}     (nested legacy)
          - {"result": [...]}               (result IS the list)
          - {"result": {...}}               (result IS a single object)
          - {"articles": [...]}             (news search)
          - {"scoops": [...]}               (scoops search)
          - {"technologies": [...]}         (tech enrich)
          - {"signals": [...]}              (intent enrich)
          - {"contacts": [...]}             (contact search flat)
          - {"people": [...]}               (flat variant)

        JSON:API records with {"attributes": {...}} are automatically unwrapped
        to flat dicts for downstream normalization compatibility.
        """
        # Primary key: "data"
        if "data" in response:
            d = response["data"]
            if isinstance(d, list):
                return self._unwrap_jsonapi(d)
            if isinstance(d, dict) and d:
                # Single-object response — normalise to list
                return self._unwrap_jsonapi([d])
            return []

        # "result" key — may be dict-with-data, a list, or a bare object
        if "result" in response:
            inner = response["result"]
            if isinstance(inner, list):
                # ZoomInfo batch enrich format:
                #   result: [{input: {...}, data: [...], matchStatus: "MATCH"|"NO_MATCH"|"INVALID_INPUT"}]
                # The outer list contains one wrapper per input, not the actual records.
                # Extract the real company/entity data from inside each matched item.
                if inner and isinstance(inner[0], dict) and "matchStatus" in inner[0]:
                    matched: list = []
                    for item in inner:
                        if item.get("matchStatus") in ("MATCH", "PARTIAL_MATCH"):
                            item_data = item.get("data", [])
                            if isinstance(item_data, list):
                                matched.extend(
                                    d for d in item_data
                                    if isinstance(d, dict) and "errorMessage" not in d
                                )
                            elif isinstance(item_data, dict) and "errorMessage" not in item_data and item_data:
                                matched.append(item_data)
                    return matched
                # Plain list (non-batch) — return as-is
                return inner
            if isinstance(inner, dict):
                if "data" in inner:
                    d = inner["data"]
                    if isinstance(d, list):
                        return d
                    if isinstance(d, dict) and d:
                        return [d]
                elif inner:
                    # result IS the data object (no nested "data" key)
                    return [inner]

        # Domain-specific list keys used by ZoomInfo endpoint responses
        for key in (
            "articles", "news",                     # /search/news
            "scoops", "scoop",                       # /search/scoop
            "technologies", "technology",            # /enrich/technology
            "signals", "intent", "intentSignals",    # /enrich/intent
            "contacts", "people", "persons",         # contact endpoints
            "results", "items",                      # generic fallbacks
        ):
            if key in response and isinstance(response[key], list):
                return response[key]

        # Log unexpected format to aid debugging
        logger.warning(f"ZoomInfo: unrecognised response format — keys: {list(response.keys())}")
        return []

    @staticmethod
    def _normalize_website(domain: str) -> str:
        """
        Normalize a bare domain to the URL format ZoomInfo requires.
        ZoomInfo companyWebsite must be in 'http://www.example.com' format.
        Passing a bare domain like 'microsoft.com' returns 0 results.
        """
        if not domain:
            return domain
        domain = domain.strip().rstrip("/")
        if not domain.startswith("http://") and not domain.startswith("https://"):
            domain = f"https://{domain}"
        return domain

    @staticmethod
    def _website_candidates(domain: str) -> str:
        """
        Build a comma-separated list of all URL format variants for a domain.
        ZoomInfo's companyWebsite field accepts a comma-separated list, so passing
        multiple variants maximises the chance of matching however ZoomInfo stores
        the company's website (with/without www, http/https, bare domain).
        """
        # Strip any existing scheme and www prefix to get the bare hostname
        bare = domain.strip().rstrip("/")
        for prefix in ("https://www.", "http://www.", "https://", "http://", "www."):
            if bare.startswith(prefix):
                bare = bare[len(prefix):]
                break

        candidates = [
            f"https://www.{bare}",   # ZoomInfo-documented format
            f"https://{bare}",
            f"http://www.{bare}",
            bare,                    # Some legacy records may use bare domain
        ]
        return ",".join(candidates)

    @staticmethod
    def _bare_domain(domain: str) -> str:
        """Strip scheme and www prefix to return a bare hostname (e.g. 'microsoft.com')."""
        bare = domain.strip().rstrip("/")
        for prefix in ("https://www.", "http://www.", "https://", "http://", "www."):
            if bare.startswith(prefix):
                bare = bare[len(prefix):]
                break
        return bare

    @staticmethod
    def _primary_website(domain: str) -> str:
        """
        Return the single canonical URL for a domain in ZoomInfo's preferred format.
        ZoomInfo enrich endpoints do EXACT URL matching — they do NOT accept
        comma-separated lists.  Always use this for enrich (not search) payloads.
        """
        if not domain:
            return domain
        bare = ZoomInfoClient._bare_domain(domain)
        return f"https://www.{bare}"

    @staticmethod
    def _company_name_from_domain(domain: str) -> str:
        """Derive a best-guess company name from a domain (e.g. 'microsoft.com' → 'Microsoft')."""
        bare = ZoomInfoClient._bare_domain(domain)
        # Use the part before the first dot and capitalise it
        name = bare.split(".")[0]
        return name.capitalize() if name else ""

    async def enrich_company(
        self,
        domain: Optional[str] = None,
        company_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enrich company data by domain or name.

        ZoomInfo enrich endpoints do EXACT URL matching — they do NOT accept
        comma-separated lists.  We try URL formats in order:
          1. https://www.{domain}  (ZoomInfo's documented canonical format)
          2. https://{domain}      (no-www variant)
          3. companyName           (name-only fallback)

        Returns:
            Dict with success, data (raw), normalized (standard fields), error
        """
        if not domain and not company_name:
            return {"success": False, "data": {}, "normalized": {}, "error": "No domain or company name provided"}

        # Build ordered list of JSON:API payloads to attempt.
        # GTM API v1 uses JSON:API format: {"data": {"type": "CompanyEnrich", "attributes": {...}}}
        # Identifiers: companyWebsite (full URL), companyName, companyId.
        # outputFields specifies which fields to return.
        attrs_to_try: List[Dict[str, Any]] = []
        if domain:
            bare = self._bare_domain(domain)
            for website in (f"https://www.{bare}", f"https://{bare}"):
                attrs_to_try.append({"companyWebsite": website, "outputFields": COMPANY_OUTPUT_FIELDS})
            if company_name:
                attrs_to_try.append({"companyWebsite": f"https://www.{bare}", "companyName": company_name, "outputFields": COMPANY_OUTPUT_FIELDS})
        if company_name:
            attrs_to_try.append({"companyName": company_name, "outputFields": COMPANY_OUTPUT_FIELDS})

        last_error: Optional[str] = None
        for attrs in attrs_to_try:
            payload = {"data": {"type": "CompanyEnrich", "attributes": attrs}}
            try:
                response = await self._make_request(ENDPOINTS["company_enrich"], payload)
                data_list = self._extract_data_list(response)
                if data_list:
                    raw = data_list[0]
                    normalized = self._normalize_company_data(raw)
                    logger.info(
                        "ZoomInfo company enrich success with attrs=%s company_id=%s",
                        list(attrs.keys()), normalized.get("company_id")
                    )
                    return {"success": True, "data": raw, "normalized": normalized, "error": None}
                logger.debug(
                    "ZoomInfo company enrich: no data for attrs=%s, trying next",
                    list(attrs.keys())
                )
            except httpx.TimeoutException:
                logger.warning("ZoomInfo company enrich timed out")
                return {"success": False, "data": {}, "normalized": {}, "error": "Request timeout"}
            except httpx.HTTPStatusError as e:
                last_error = self._http_error_detail(e)
                logger.warning("ZoomInfo company enrich %s for attrs=%s", last_error, list(attrs.keys()))
                if e.response.status_code not in (400, 404, 422):
                    return {"success": False, "data": {}, "normalized": {}, "error": last_error}
            except Exception as e:
                last_error = str(e)
                logger.error("ZoomInfo company enrich exception: %s", e)

        return {"success": False, "data": {}, "normalized": {}, "error": last_error or "No company data found"}

    async def search_contacts(
        self,
        domain: str,
        job_titles: Optional[List[str]] = None,
        max_results: int = 25
    ) -> Dict[str, Any]:
        """
        Search for executive and key contacts at a company.

        Priority order (per Intercept requirements):
        1. CTO, CFO, CMO, CIO — primary target personas, by job title
        2. Other C-Suite (CEO, COO, CRO, CPO, etc.) — by job title
        3. C-Level management level (broader net for any missed chiefs)
        4. VP-Level, then Director-Level as additional coverage
        5. Unfiltered fallbacks if all above yield nothing

        Partners are excluded from all results.
        North America (US, Canada, Mexico) is preferred via geo filter;
        if geo-filtered search returns 0, falls back to global.

        Returns:
            Dict with success, people (priority-sorted normalized list), error
        """
        all_people: List[Dict[str, Any]] = []
        seen_ids: set = set()
        last_error: Optional[str] = None

        website_candidates = self._website_candidates(domain)

        def _add_contacts(data_list: list) -> int:
            """Deduplicate, exclude partners, and append to all_people. Returns count added."""
            added = 0
            for c in data_list:
                person = self._normalize_contact(c)
                if self._is_partner(person.get("title", "")):
                    logger.debug("ZoomInfo: skipping partner title: %s", person.get("title"))
                    continue
                pid = person.get("person_id") or person.get("email") or person.get("name")
                if pid and pid not in seen_ids:
                    seen_ids.add(pid)
                    all_people.append(person)
                    added += 1
            return added

        async def _search(search_attrs: Dict[str, Any], label: str) -> int:
            """
            POST contact_search with JSON:API format.
            GTM API v1 requires: {"data": {"type": "ContactSearch", "attributes": {...}}}
            Pagination uses query params: ?page[size]=N&page[number]=N
            Returns count of new contacts added.
            """
            nonlocal last_error
            # Extract page size from attributes (rpp) and pass as query param
            page_size = search_attrs.pop("rpp", None)
            query_params = {"page[size]": page_size} if page_size else None
            payload = {"data": {"type": "ContactSearch", "attributes": search_attrs}}
            try:
                response = await self._make_request(ENDPOINTS["contact_search"], payload, params=query_params)
                data_list = self._extract_data_list(response)
                if data_list:
                    added = _add_contacts(data_list)
                    logger.info(
                        "ZoomInfo %s: %d results, %d new contacts added",
                        label, len(data_list), added
                    )
                    return added
                logger.warning(
                    "ZoomInfo %s: 0 contacts for domain=%s",
                    label, domain
                )
            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}"
                logger.error("ZoomInfo %s HTTP error: %s", label, e)
            except Exception as e:
                last_error = str(e)
                logger.error("ZoomInfo %s failed: %s", label, e)
            return 0

        async def _search_na_first(base_attrs: Dict[str, Any], label: str) -> int:
            """
            Try contact search with North America geo filter first, then global.
            Maximises NA coverage without hard-failing when geo returns nothing
            (some companies have no NA contacts in ZoomInfo, or the field isn't
            supported for a given search type).
            """
            na_attrs = {**base_attrs, "country": NORTH_AMERICA_COUNTRIES}
            count = await _search(na_attrs, f"{label} [NA]")
            if count > 0:
                return count
            logger.info("ZoomInfo %s: NA geo returned 0, falling back to global", label)
            return await _search(base_attrs, f"{label} [global]")

        rpp = min(max_results, 10)

        # --- Strategy 1: C-Level by managementLevel (most reliable ZoomInfo filter) ---
        # This is the backbone — ZoomInfo's own classification catches all C-Suite
        # regardless of exact title wording (avoids jobTitle exact-match misses on
        # large companies like Amazon where titles vary widely).
        if len(all_people) < max_results:
            await _search_na_first(
                {"companyWebsite": website_candidates, "managementLevel": ["C-Level"], "rpp": rpp},
                "C-Level"
            )

        # --- Strategy 2: Explicit priority C-Suite by jobTitle (CTO, CFO, CMO, CIO) ---
        # Supplementary pass to catch any priority titles missed by managementLevel.
        # Uses the caller's job_titles override if provided, otherwise PRIORITY_CSUITE_TITLES.
        if len(all_people) < max_results:
            titles = job_titles if job_titles else PRIORITY_CSUITE_TITLES
            await _search_na_first(
                {"companyWebsite": website_candidates, "jobTitle": titles, "rpp": rpp},
                "priority-csuite"
            )

        # --- Strategy 3: Other C-Suite by jobTitle (CEO, COO, CRO, CPO, etc.) ---
        if len(all_people) < max_results and job_titles is None:
            await _search_na_first(
                {"companyWebsite": website_candidates, "jobTitle": OTHER_CSUITE_TITLES, "rpp": rpp},
                "other-csuite"
            )

        # --- Strategy 4: VP-Level ---
        if len(all_people) < max_results:
            await _search_na_first(
                {"companyWebsite": website_candidates, "managementLevel": ["VP-Level"], "rpp": rpp},
                "VP-Level"
            )

        # --- Strategy 5: Director-Level ---
        if len(all_people) < max_results:
            await _search_na_first(
                {"companyWebsite": website_candidates, "managementLevel": ["Director-Level"], "rpp": rpp},
                "Director-Level"
            )

        # --- Strategy 6: No-filter fallback (all roles, all regions) ---
        if not all_people:
            await _search(
                {"companyWebsite": website_candidates, "rpp": max_results},
                "no-filter fallback"
            )

        # --- Strategy 7: Company name fallback ---
        # ZoomInfo stores company names separately from URLs — this catches cases
        # where the website-based lookup finds nothing.
        if not all_people:
            company_name = self._company_name_from_domain(domain)
            if company_name:
                await _search(
                    {"companyName": company_name, "rpp": max_results},
                    f"companyName={company_name} fallback"
                )

        # Sort: CTO/CFO/CMO/CIO first → other C-Suite → VP → Director → other.
        # This sorting is the primary mechanism for surfacing priority contacts —
        # it works regardless of which search strategy actually found them.
        all_people.sort(key=self._contact_priority)

        logger.info("ZoomInfo total contacts: %d for domain=%s", len(all_people), domain)
        if all_people:
            return {"success": True, "people": all_people, "error": None}
        return {
            "success": False if last_error else True,
            "people": [],
            "error": last_error or "No contacts found for this domain in ZoomInfo"
        }

    async def enrich_contacts(
        self,
        person_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Enrich contacts by person IDs for full profile data including
        directPhone, mobilePhone, companyPhone, contactAccuracyScore,
        department, and managementLevel.

        Uses GTM API v1 JSON:API format with outputFields to explicitly
        request phone number data.  The contact SEARCH endpoint does NOT
        return phone/email — only this enrich endpoint does.

        Returns:
            Dict with success, people (enriched normalized list), error
        """
        if not person_ids:
            return {"success": True, "people": [], "error": None}

        payload = {
            "data": {
                "type": "ContactEnrich",
                "attributes": {
                    "personId": person_ids,
                    "outputFields": CONTACT_ENRICH_OUTPUT_FIELDS,
                }
            }
        }

        try:
            response = await self._make_request(ENDPOINTS["contact_enrich"], payload)
            data_list = self._extract_data_list(response)
            people = [self._normalize_contact(c) for c in data_list]
            return {"success": True, "people": people, "error": None}

        except httpx.TimeoutException:
            logger.warning("ZoomInfo contact enrich timed out")
            return {"success": False, "people": [], "error": "Request timeout"}
        except httpx.HTTPStatusError as e:
            logger.warning(f"ZoomInfo contact enrich HTTP error: {e.response.status_code}")
            return {"success": False, "people": [], "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            logger.error(f"ZoomInfo contact enrich failed: {e}")
            return {"success": False, "people": [], "error": str(e)}

    async def search_and_enrich_contacts(
        self,
        domain: str,
        job_titles: Optional[List[str]] = None,
        max_results: int = 25
    ) -> Dict[str, Any]:
        """
        Two-step contact enrichment: Search → Enrich.
        First searches for contacts, then enriches with full profile data
        including phone numbers and accuracy scores.

        Returns:
            Dict with success, people (fully enriched), error
        """
        # Step 1: Search for contacts
        search_result = await self.search_contacts(
            domain=domain, job_titles=job_titles, max_results=max_results
        )
        if not search_result.get("success") or not search_result.get("people"):
            return search_result

        # Step 2: Extract person IDs and enrich
        person_ids = [
            p.get("person_id") for p in search_result["people"]
            if p.get("person_id")
        ]

        if not person_ids:
            # No person IDs available, return search results as-is
            return search_result

        enrich_result = await self.enrich_contacts(person_ids=person_ids)
        if enrich_result.get("success") and enrich_result.get("people"):
            return enrich_result

        # Fall back to search results if enrich fails
        logger.warning("Contact enrich failed, returning search results")
        return search_result

    async def lookup_contacts_by_identity(
        self,
        contacts: List[Dict[str, Any]],
        domain: str,
        max_contacts: int = 10,
    ) -> Dict[str, Any]:
        """
        Search ZoomInfo GTM contact search endpoint for specific contacts by
        identity (email or first+last name + domain).

        Used to cross-reference Apollo/Hunter contacts against ZoomInfo to
        retrieve their direct phone, mobile phone, and company phone numbers.

        This deliberately uses the GTM contact SEARCH endpoint (not the
        /contacts/enrich endpoint) because the enrich endpoint requires a valid
        ZoomInfo personId which Apollo/Hunter contacts do not have.

        Lookups are run concurrently (up to max_contacts at a time) to keep
        pipeline latency low.

        Args:
            contacts:     List of dicts with any of: name, first_name, last_name, email
            domain:       Company domain to scope the search
            max_contacts: Cap on how many contacts to look up (default 10)

        Returns:
            Dict with success, people (list of normalized contacts with phones), error
        """
        if not contacts:
            return {"success": True, "people": [], "error": None}

        # Cap the number of contacts to avoid excessive API calls
        contacts_to_lookup = contacts[:max_contacts]

        async def _lookup_one(contact: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            email = (contact.get("email") or "").strip()
            name = (contact.get("name") or "").strip()
            first_name = (contact.get("first_name") or "").strip()
            last_name = (contact.get("last_name") or "").strip()

            # Derive first/last from full name if not split yet
            if name and not (first_name and last_name):
                parts = name.split(None, 1)
                first_name = first_name or (parts[0] if parts else "")
                last_name = last_name or (parts[1] if len(parts) > 1 else "")

            payloads_to_try = []

            website_candidates = ZoomInfoClient._website_candidates(domain)

            # Email-based lookup is most precise — try first
            if email:
                payloads_to_try.append({
                    "data": {
                        "type": "ContactSearch",
                        "attributes": {
                            "companyWebsite": website_candidates,
                            "email": email,
                            "rpp": 1,
                        }
                    }
                })

            # Name-based lookup as fallback
            if first_name and last_name:
                payloads_to_try.append({
                    "data": {
                        "type": "ContactSearch",
                        "attributes": {
                            "companyWebsite": website_candidates,
                            "firstName": first_name,
                            "lastName": last_name,
                            "rpp": 1,
                        }
                    }
                })

            if not payloads_to_try:
                logger.debug("ZoomInfo identity lookup: skipping contact with no email/name")
                return None

            for payload in payloads_to_try:
                try:
                    response = await self._make_request(ENDPOINTS["contact_search"], payload)
                    data_list = self._extract_data_list(response)
                    if data_list:
                        return self._normalize_contact(data_list[0])
                except httpx.HTTPStatusError as e:
                    logger.warning(
                        f"ZoomInfo identity lookup HTTP {e.response.status_code} "
                        f"for {email or name}: {e}"
                    )
                    continue  # Try next payload format before giving up
                except Exception as e:
                    logger.warning(f"ZoomInfo identity lookup failed for {email or name}: {e}")
                    continue  # Try next payload format before giving up

            return None

        # Run all lookups concurrently
        results = await asyncio.gather(
            *[_lookup_one(c) for c in contacts_to_lookup],
            return_exceptions=False,
        )

        # De-duplicate by person_id / email / name
        found: List[Dict[str, Any]] = []
        seen_ids: set = set()
        for person in results:
            if person is None:
                continue
            pid = person.get("person_id") or person.get("email") or person.get("name")
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                found.append(person)

        logger.info(
            f"ZoomInfo identity lookup: {len(found)}/{len(contacts_to_lookup)} contacts "
            f"found for domain={domain}"
        )
        return {"success": True, "people": found, "error": None}

    async def enrich_intent(self, domain: str, company_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get buyer intent signals for a company with full field extraction.

        Args:
            domain:     Company domain (used as fallback when company_id unavailable)
            company_id: ZoomInfo internal company ID (preferred — most reliable lookup)

        Returns:
            Dict with success, intent_signals (normalized list), raw_data, error

        GTM API v1 uses JSON:API format: {"data": {"type": "IntentEnrich", "attributes": {...}}}
        topics is MANDATORY — omitting it returns HTTP 400.
        """
        primary_website = self._primary_website(domain)

        # Ordered attribute sets: companyId (most reliable) → companyWebsite fallback.
        attrs_to_try: List[Dict[str, Any]] = []
        if company_id:
            attrs_to_try.append({"companyId": company_id, "topics": DEFAULT_INTENT_TOPICS})
        attrs_to_try.append({"companyWebsite": primary_website, "topics": DEFAULT_INTENT_TOPICS})

        last_error: Optional[str] = None
        for attrs in attrs_to_try:
            payload = {"data": {"type": "IntentEnrich", "attributes": attrs}}
            try:
                response = await self._make_request(ENDPOINTS["intent_enrich"], payload)
                raw_signals = self._extract_data_list(response)
                normalized_signals = [self._normalize_intent_signal(sig) for sig in raw_signals]
                logger.info(
                    "ZoomInfo intent enrich success: %d signals for domain=%s (attrs=%s)",
                    len(raw_signals), domain, list(attrs.keys())
                )
                return {
                    "success": True,
                    "intent_signals": normalized_signals,
                    "raw_data": raw_signals,
                    "error": None,
                }
            except httpx.TimeoutException:
                return {"success": False, "intent_signals": [], "raw_data": [], "error": "Request timeout"}
            except httpx.HTTPStatusError as e:
                detail = self._http_error_detail(e)
                last_error = detail
                logger.warning(
                    "ZoomInfo intent enrich %s for attrs=%s",
                    detail, list(attrs.keys())
                )
                if "invalid topics" in detail.lower() or "invalid number of topics" in detail.lower():
                    logger.warning(
                        "ZoomInfo Buyer Intent topics rejected — check that Buyer Intent is "
                        "enabled on the account and that topic names match the ZoomInfo taxonomy"
                    )
                    break
                if e.response.status_code not in (400, 422):
                    break
            except Exception as e:
                last_error = str(e)
                logger.error("ZoomInfo intent enrich exception: %s", e)
                break

        return {"success": False, "intent_signals": [], "raw_data": [], "error": last_error or "No intent data found"}

    async def search_scoops(
        self,
        domain: str,
        scoop_types: Optional[List[str]] = None,
        company_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search for business scoops/events at a company with full field extraction.

        Args:
            domain:      Company domain (fallback when company_id unavailable)
            scoop_types: Optional list of scoop type filters
            company_id:  ZoomInfo internal company ID (preferred identifier)

        Returns:
            Dict with success, scoops (normalized list), raw_data, error

        GTM API v1: scoops/search rejects companyId — use scoops/enrich instead.
        JSON:API format: {"data": {"type": "ScoopEnrich", "attributes": {...}}}
        """
        attrs: Dict[str, Any] = {}
        if company_id:
            attrs["companyId"] = company_id
        else:
            attrs["companyWebsite"] = self._primary_website(domain)
        if scoop_types:
            attrs["scoopTypes"] = scoop_types

        payload = {"data": {"type": "ScoopEnrich", "attributes": attrs}}

        try:
            response = await self._make_request(ENDPOINTS["scoops_enrich"], payload)
            raw_scoops = self._extract_data_list(response)
            normalized_scoops = [self._normalize_scoop(scoop) for scoop in raw_scoops]
            return {
                "success": True,
                "scoops": normalized_scoops,
                "raw_data": raw_scoops,
                "error": None
            }

        except httpx.TimeoutException:
            return {"success": False, "scoops": [], "raw_data": [], "error": "Request timeout"}
        except httpx.HTTPStatusError as e:
            detail = self._http_error_detail(e)
            logger.warning("ZoomInfo scoops search %s", detail)
            return {"success": False, "scoops": [], "raw_data": [], "error": detail}
        except Exception as e:
            logger.error(f"ZoomInfo scoops search failed: {e}")
            return {"success": False, "scoops": [], "raw_data": [], "error": str(e)}

    async def search_news(
        self,
        company_name: str,
        company_id: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search for company news articles with full field extraction.

        Args:
            company_name: Company name string
            company_id:   ZoomInfo internal company ID (preferred — more reliable lookup)
            domain:       Company domain (optional, used as companyWebsite fallback)

        Returns:
            Dict with success, articles (normalized list), raw_data, error

        GTM API v1: news/search rejects companyId/companyName — use news/enrich instead.
        JSON:API format: {"data": {"type": "NewsEnrich", "attributes": {...}}}
        """
        attrs: Dict[str, Any] = {}
        if company_id:
            attrs["companyId"] = company_id
        elif company_name:
            attrs["companyName"] = company_name
        else:
            return {"success": False, "articles": [], "raw_data": [], "error": "companyId or companyName required for news enrich"}

        payload = {"data": {"type": "NewsEnrich", "attributes": attrs}}

        try:
            response = await self._make_request(ENDPOINTS["news_enrich"], payload)
            raw_articles = self._extract_data_list(response)
            normalized_articles = [self._normalize_news_article(article) for article in raw_articles]
            logger.info(
                "ZoomInfo news search success: %d articles for company=%s",
                len(raw_articles), company_name
            )
            return {
                "success": True,
                "articles": normalized_articles,
                "raw_data": raw_articles,
                "error": None,
            }
        except httpx.TimeoutException:
            return {"success": False, "articles": [], "raw_data": [], "error": "Request timeout"}
        except httpx.HTTPStatusError as e:
            detail = self._http_error_detail(e)
            logger.warning("ZoomInfo news search %s", detail)
            return {"success": False, "articles": [], "raw_data": [], "error": detail}
        except Exception as e:
            logger.error("ZoomInfo news search exception: %s", e)
            return {"success": False, "articles": [], "raw_data": [], "error": str(e)}

    async def enrich_technologies(self, domain: str, company_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get installed technologies for a company with full field extraction.

        Args:
            domain:     Company domain (fallback when company_id unavailable)
            company_id: ZoomInfo internal company ID (preferred — API requires this)

        Returns:
            Dict with success, technologies (normalized list), raw_data, error

        GTM API v1 endpoint: /gtm/data/v1/companies/technologies/enrich
        JSON:API format: {"data": {"type": "TechnologyEnrich", "attributes": {...}}}
        """
        primary_website = self._primary_website(domain)

        attrs: Dict[str, Any] = {}
        if company_id:
            attrs["companyId"] = company_id
        else:
            attrs["companyWebsite"] = primary_website

        payload = {"data": {"type": "TechnologyEnrich", "attributes": attrs}}

        try:
            response = await self._make_request(ENDPOINTS["tech_enrich"], payload)
            raw_technologies = self._extract_data_list(response)
            normalized_technologies = [self._normalize_technology(tech) for tech in raw_technologies]
            logger.info(
                "ZoomInfo tech enrich success: %d technologies for domain=%s",
                len(raw_technologies), domain
            )
            return {
                "success": True,
                "technologies": normalized_technologies,
                "raw_data": raw_technologies,
                "error": None,
            }
        except httpx.TimeoutException:
            return {"success": False, "technologies": [], "raw_data": [], "error": "Request timeout"}
        except httpx.HTTPStatusError as e:
            detail = self._http_error_detail(e)
            logger.warning("ZoomInfo tech enrich %s", detail)
            return {"success": False, "technologies": [], "raw_data": [], "error": detail}
        except Exception as e:
            logger.error("ZoomInfo tech enrich exception: %s", e)
            return {"success": False, "technologies": [], "raw_data": [], "error": str(e)}

    @staticmethod
    def _is_partner(title: str) -> bool:
        """
        Return True if the job title indicates a Partner role (to be excluded).

        Catches: "Partner", "Managing Partner", "Senior Partner",
                 "General Partner", "Partner, Technology", "Partner – Digital".
        Does NOT catch: "Partnership Manager", "Channel Partner Director",
                        "Director of Partnerships", "Strategic Partner Manager".
        """
        if not title:
            return False
        t = title.strip().lower()
        # Exact match
        if t == "partner":
            return True
        # Ends with " partner" (e.g. "Managing Partner", "Senior Partner", "General Partner")
        if t.endswith(" partner"):
            return True
        # Starts with "partner," or "partner -/–" (e.g. "Partner, Technology", "Partner – Digital")
        if t.startswith("partner,") or re.match(r"^partner\s*[-–]", t):
            return True
        return False

    @staticmethod
    def _contact_priority(person: Dict[str, Any]) -> int:
        """
        Return sort key for contacts — lower value = shown first.

        Priority 0: CTO, CFO, CMO, CIO  (Intercept primary targets)
        Priority 1: Other C-Suite chiefs (CEO, COO, CRO, CISO, etc.)
        Priority 2: VP-Level
        Priority 3: Director-Level
        Priority 4: Other / unknown
        """
        title = (person.get("title") or "").lower()
        mgmt = (person.get("management_level") or "").lower()

        # Priority 0: CTO, CFO, CMO, CIO
        # Use word boundaries to avoid false matches (e.g. CISO should not count as CIO)
        cto = re.search(r"\bchief technology officer\b|\bcto\b", title)
        cfo = re.search(r"\bchief financial officer\b|\bcfo\b", title)
        cmo = re.search(r"\bchief marketing officer\b|\bcmo\b", title)
        # CIO: match "chief information officer" but NOT "chief information security officer"
        cio = (
            re.search(r"\bchief information officer\b", title)
            or (re.search(r"\bcio\b", title) and not re.search(r"\bciso\b", title))
        )
        if any([cto, cfo, cmo, cio]):
            return 0

        # Priority 1: other C-Suite / C-Level
        if "chief" in title or "c-level" in mgmt:
            return 1

        # Priority 2: VP-Level
        if "vp-level" in mgmt or re.search(r"\bvice president\b|\bvp\b|\bsvp\b|\bevp\b", title):
            return 2

        # Priority 3: Director-Level
        if "director-level" in mgmt or "director" in title:
            return 3

        return 4

    @staticmethod
    def _normalize_scoop(raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize ZoomInfo scoop/business event to extract ALL fields.

        Scoops include: funding, acquisitions, new hires, expansions, partnerships,
        product launches, awards, and other significant business events.

        ZoomInfo uses JSON:API format, so data may be in 'attributes' field.
        """
        attrs = raw.get("attributes", raw)
        return {
            # Identification
            "scoop_id": attrs.get("scoopId", attrs.get("id", "")),
            "scoop_type": attrs.get("scoopType", attrs.get("type", "")),
            "title": attrs.get("title", attrs.get("headline", "")),

            # Content
            "description": attrs.get("description", attrs.get("summary", "")),
            "full_text": attrs.get("fullText", attrs.get("body", "")),
            "snippet": attrs.get("snippet", ""),

            # Temporal
            "date": attrs.get("date", attrs.get("publishedDate", "")),
            "published_date": attrs.get("publishedDate", attrs.get("date", "")),
            "discovered_date": attrs.get("discoveredDate", ""),
            "last_updated": attrs.get("lastUpdated", ""),

            # Source
            "source": attrs.get("source", ""),
            "source_url": attrs.get("sourceUrl", attrs.get("url", "")),
            "author": attrs.get("author", ""),

            # Classification
            "category": attrs.get("category", ""),
            "tags": attrs.get("tags", []),
            "keywords": attrs.get("keywords", []),

            # Impact & relevance
            "relevance_score": attrs.get("relevanceScore", 0),
            "importance": attrs.get("importance", ""),
            "sentiment": attrs.get("sentiment", ""),

            # Additional details (type-specific)
            "amount": attrs.get("amount", ""),  # for funding
            "investors": attrs.get("investors", []),  # for funding
            "person_name": attrs.get("personName", ""),  # for new hires
            "person_title": attrs.get("personTitle", ""),  # for new hires
            "location": attrs.get("location", ""),  # for expansions
            "partner_name": attrs.get("partnerName", ""),  # for partnerships
        }

    @staticmethod
    def _normalize_news_article(raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize ZoomInfo news article to extract ALL fields.
        """
        attrs = raw.get("attributes", raw)
        return {
            # Identification
            "article_id": attrs.get("articleId", attrs.get("id", "")),
            "title": attrs.get("title", attrs.get("headline", "")),

            # Content
            "description": attrs.get("description", attrs.get("summary", "")),
            "full_text": attrs.get("fullText", attrs.get("body", attrs.get("content", ""))),
            "snippet": attrs.get("snippet", ""),
            "excerpt": attrs.get("excerpt", ""),

            # Source
            "source": attrs.get("source", attrs.get("publisher", "")),
            "url": attrs.get("url", attrs.get("sourceUrl", "")),
            "author": attrs.get("author", ""),
            "source_domain": attrs.get("sourceDomain", ""),

            # Temporal
            "published_date": attrs.get("publishedDate", attrs.get("date", "")),
            "discovered_date": attrs.get("discoveredDate", ""),
            "last_updated": attrs.get("lastUpdated", ""),

            # Classification
            "category": attrs.get("category", ""),
            "subcategory": attrs.get("subcategory", ""),
            "tags": attrs.get("tags", []),
            "keywords": attrs.get("keywords", []),
            "topics": attrs.get("topics", []),

            # Engagement & impact
            "relevance_score": attrs.get("relevanceScore", 0),
            "sentiment": attrs.get("sentiment", ""),
            "sentiment_score": attrs.get("sentimentScore", 0),
            "language": attrs.get("language", "en"),

            # Media
            "image_url": attrs.get("imageUrl", attrs.get("thumbnailUrl", "")),
            "video_url": attrs.get("videoUrl", ""),
        }

    @staticmethod
    def _normalize_technology(raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize ZoomInfo technology installation data to extract ALL fields.
        """
        attrs = raw.get("attributes", raw)
        return {
            # Technology identification
            "tech_id": attrs.get("technologyId", attrs.get("id", "")),
            "tech_name": attrs.get("technologyName", attrs.get("name", attrs.get("technology", ""))),
            "product_name": attrs.get("productName", ""),
            "vendor": attrs.get("vendor", attrs.get("vendorName", "")),

            # Classification
            "category": attrs.get("category", ""),
            "subcategory": attrs.get("subcategory", ""),
            "tech_type": attrs.get("technologyType", attrs.get("type", "")),
            "tags": attrs.get("tags", []),

            # Installation details
            "install_date": attrs.get("installDate", attrs.get("installedDate", "")),
            "first_seen": attrs.get("firstSeen", ""),
            "last_seen": attrs.get("lastSeen", ""),
            "status": attrs.get("status", "active"),  # active, inactive, unknown

            # Usage & adoption
            "adoption_level": attrs.get("adoptionLevel", ""),  # enterprise-wide, departmental, etc.
            "usage_frequency": attrs.get("usageFrequency", ""),
            "user_count": attrs.get("userCount", 0),
            "license_count": attrs.get("licenseCount", 0),

            # Technical details
            "version": attrs.get("version", ""),
            "deployment_type": attrs.get("deploymentType", ""),  # cloud, on-premise, hybrid
            "integration_points": attrs.get("integrationPoints", []),

            # Confidence & quality
            "confidence_score": attrs.get("confidenceScore", 0),
            "data_source": attrs.get("dataSource", ""),
            "last_verified": attrs.get("lastVerified", ""),
        }

    @staticmethod
    def _normalize_intent_signal(raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize ZoomInfo intent signal to extract ALL fields.

        ZoomInfo intent signals contain:
        - Topic identification: topicId, topicName, topic
        - Scoring: intentScore, score, audienceStrength
        - Context: description, category, subcategory
        - Temporal: lastSeen, firstSeen, timestamp
        - Engagement: activityLevel, engagementScore
        """
        attrs = raw.get("attributes", raw)
        return {
            # Topic identification
            "topic_id": attrs.get("topicId", attrs.get("id", "")),
            "topic": attrs.get("topicName", attrs.get("topic", attrs.get("name", ""))),
            "topic_name": attrs.get("topicName", attrs.get("topic", "")),

            # Scoring metrics
            "intent_score": attrs.get("intentScore", attrs.get("score", 0)),
            "score": attrs.get("intentScore", attrs.get("score", 0)),
            "audience_strength": attrs.get("audienceStrength", attrs.get("strength", "")),
            "engagement_score": attrs.get("engagementScore", 0),
            "activity_level": attrs.get("activityLevel", ""),

            # Context and classification
            "description": attrs.get("description", ""),
            "category": attrs.get("category", ""),
            "subcategory": attrs.get("subcategory", ""),
            "keywords": attrs.get("keywords", []),
            "topic_type": attrs.get("topicType", attrs.get("type", "")),

            # Temporal information
            "last_seen": attrs.get("lastSeen", attrs.get("lastSeenDate", "")),
            "first_seen": attrs.get("firstSeen", attrs.get("firstSeenDate", "")),
            "timestamp": attrs.get("timestamp", ""),
            "duration_days": attrs.get("durationDays", 0),

            # Additional metrics
            "research_count": attrs.get("researchCount", 0),
            "page_views": attrs.get("pageViews", 0),
            "unique_visitors": attrs.get("uniqueVisitors", 0),
            "trend": attrs.get("trend", ""),  # increasing, stable, decreasing

            # Confidence and quality
            "confidence": attrs.get("confidence", attrs.get("confidenceScore", 0)),
            "data_quality": attrs.get("dataQuality", ""),
        }

    @staticmethod
    def _normalize_company_data(raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize ZoomInfo fields to extract ALL available company data.

        Extracts comprehensive firmographic data including:
        - Basic info: name, domain, description
        - Financial: revenue, revenue range, employee count
        - Contact: phone, fax, emails
        - Social: LinkedIn, Facebook, Twitter
        - Classification: industry, sub-industry, SIC, NAICS codes
        - Location: address, city, state, zip, country
        - Leadership: CEO, executives
        - Other: founded year, ticker symbol, company type

        ZoomInfo uses JSON:API format, so data may be in 'attributes' field.
        """
        # Handle JSON:API format where data is nested in 'attributes'
        attrs = raw.get("attributes", raw)

        # Location data
        city = attrs.get("city", "")
        state = attrs.get("state", "")
        country = attrs.get("country", "")
        headquarters = ", ".join(filter(None, [city, state, country]))

        # Full address if available
        street = attrs.get("street", attrs.get("address", ""))
        zip_code = attrs.get("zipCode", attrs.get("zip", ""))
        full_address = ", ".join(filter(None, [street, city, state, zip_code, country]))

        return {
            # Basic identification
            "company_name": attrs.get("companyName", ""),
            "domain": attrs.get("domain", attrs.get("website", "")),
            "company_type": attrs.get("companyType", attrs.get("type", "")),
            "description": attrs.get("description", attrs.get("companyDescription", "")),

            # Financial data
            "employee_count": attrs.get("employeeCount", attrs.get("employees", "")),
            "employees_range": attrs.get("employeesRange", attrs.get("employeeRange", "")),
            "revenue": attrs.get("revenue", attrs.get("revenueUSD", "")),
            "revenue_range": attrs.get("revenueRange", ""),
            "estimated_revenue": attrs.get("estimatedRevenue", ""),

            # Industry classification
            "industry": attrs.get("industry", attrs.get("primaryIndustry", "")),
            "sub_industry": attrs.get("subIndustry", attrs.get("secondaryIndustry", "")),
            "industry_category": attrs.get("industryCategory", ""),
            "sic_codes": attrs.get("sicCodes", attrs.get("sic", [])),
            "naics_codes": attrs.get("naicsCodes", attrs.get("naics", [])),

            # Location
            "headquarters": headquarters,
            "full_address": full_address,
            "street": street,
            "city": city,
            "state": state,
            "zip_code": zip_code,
            "country": country,
            "metro_area": attrs.get("metroArea", ""),

            # Contact information
            "phone": attrs.get("phone", attrs.get("phoneNumber", "")),
            "fax": attrs.get("fax", attrs.get("faxNumber", "")),
            "corporate_email": attrs.get("email", attrs.get("corporateEmail", "")),

            # Social media & web presence
            "linkedin_url": attrs.get("linkedInUrl", attrs.get("linkedinUrl", attrs.get("linkedin", ""))),
            "facebook_url": attrs.get("facebookUrl", attrs.get("facebook", "")),
            "twitter_url": attrs.get("twitterUrl", attrs.get("twitter", "")),
            "website": attrs.get("website", attrs.get("websiteUrl", "")),

            # Leadership
            "ceo": attrs.get("ceoName", attrs.get("ceo", "")),
            "cfo": attrs.get("cfoName", attrs.get("cfo", "")),
            "cto": attrs.get("ctoName", attrs.get("cto", "")),
            "executives": attrs.get("executives", []),

            # Organizational details
            "founded_year": attrs.get("yearFounded", attrs.get("foundedYear", "")),
            "ticker": attrs.get("ticker", attrs.get("tickerSymbol", "")),
            "stock_exchange": attrs.get("stockExchange", ""),
            "parent_company": attrs.get("parentCompany", ""),
            "ownership_type": attrs.get("ownershipType", attrs.get("ownership", "")),

            # Additional firmographic data
            "company_size": attrs.get("companySize", ""),
            "fiscal_year_end": attrs.get("fiscalYearEnd", ""),
            "legal_name": attrs.get("legalName", ""),
            "dba_name": attrs.get("dbaName", attrs.get("doingBusinessAs", "")),
            "former_names": attrs.get("formerNames", []),

            # Technology & operations
            "technologies": attrs.get("technologies", []),
            "tech_install_count": attrs.get("techInstallCount", 0),
            "alexa_rank": attrs.get("alexaRank", ""),
            "fortune_rank": attrs.get("fortuneRank", ""),

            # Growth metrics
            "one_year_employee_growth": attrs.get("oneYearEmployeeGrowthRate", ""),
            "two_year_employee_growth": attrs.get("twoYearEmployeeGrowthRate", ""),
            "funding_amount": attrs.get("fundingAmount", ""),
            "fortune_rank": attrs.get("fortuneRank", ""),
            "business_model": attrs.get("businessModel", ""),
            "num_locations": attrs.get("numLocations", ""),

            # Additional metadata
            # ZoomInfo may return the company ID as an integer or under several field names.
            # Normalise to a non-empty string so downstream callers can safely do `or None`.
            "company_id": str(
                attrs.get("companyId") or attrs.get("id") or attrs.get("objectId") or
                raw.get("companyId") or raw.get("id") or ""
            ) or "",
            "logo_url": attrs.get("logoUrl", attrs.get("logo", "")),
            "last_updated": attrs.get("lastUpdated", ""),
            "data_quality_score": attrs.get("dataQualityScore", attrs.get("confidenceScore", "")),
        }

    @staticmethod
    def _normalize_contact(raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize ZoomInfo contact with full profile data.

        Includes phone numbers (direct, mobile, company), accuracy scores,
        department, and management level from Contact Enrich endpoint.

        ZoomInfo uses JSON:API format, so data may be in 'attributes' field.
        """
        # Handle JSON:API format where data is nested in 'attributes'
        attrs = raw.get("attributes", raw)

        # Extract name fields with multiple possible locations
        first_name = attrs.get("firstName", attrs.get("firstname", attrs.get("first_name", "")))
        last_name = attrs.get("lastName", attrs.get("lastname", attrs.get("last_name", "")))

        # If still N/A or empty, try alternate fields
        if not first_name or first_name == "N/A":
            first_name = attrs.get("givenName", attrs.get("given_name", ""))
        if not last_name or last_name == "N/A":
            last_name = attrs.get("familyName", attrs.get("family_name", attrs.get("surname", "")))

        # Try fullName if individual fields not available
        full_name = attrs.get("fullName", attrs.get("full_name", attrs.get("name", "")))
        name = full_name if full_name else f"{first_name} {last_name}".strip()

        # If name is still empty or N/A, use a placeholder
        if not name or name.strip() == "N/A N/A" or name.strip() == "N/A":
            name = "Contact"

        return {
            "name": name,
            "first_name": first_name,
            "last_name": last_name,
            "title": attrs.get("jobTitle", attrs.get("job_title", attrs.get("title", ""))),
            "email": attrs.get("email", attrs.get("emailAddress", "")),
            "phone": attrs.get("phone", attrs.get("phoneNumber", "")),
            "linkedin": attrs.get("linkedInUrl", attrs.get("linkedin_url", attrs.get("linkedin", ""))),
            "direct_phone": attrs.get("directPhone", attrs.get("direct_phone", "")),
            "mobile_phone": attrs.get("mobilePhone", attrs.get("mobile_phone", "")),
            "company_phone": attrs.get("companyPhone", attrs.get("company_phone", "")),
            "contact_accuracy_score": attrs.get("contactAccuracyScore", attrs.get("accuracy_score", 0)),
            "department": attrs.get("department", ""),
            "management_level": attrs.get("managementLevel", attrs.get("management_level", "")),
            "person_id": attrs.get("personId", attrs.get("person_id", attrs.get("id", raw.get("id", "")))),
        }
