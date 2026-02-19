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
import time
from typing import Dict, Any, List, Optional

import httpx

logger = logging.getLogger(__name__)

ZOOMINFO_BASE_URL = "https://api.zoominfo.com/gtm"
ZOOMINFO_TOKEN_URL = "https://okta-login.zoominfo.com/oauth2/default/v1/token"

ENDPOINTS = {
    "company_enrich": "/data/v1/companies/enrich",
    "contact_search": "/data/v1/contacts/search",
    "contact_enrich": "/data/v1/contacts/enrich",
    "intent_enrich": "/data/v1/intent/enrich",
    "scoops_search": "/data/v1/scoops/search",
    "news_search": "/data/v1/news/search",
    "tech_enrich": "/data/v1/technologies/enrich",
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

# Full C-suite job title list — covers all chiefs, not just CEO/CTO/COO.
CSUITE_JOB_TITLES = [
    "Chief Executive Officer", "CEO",
    "Chief Technology Officer", "CTO",
    "Chief Information Officer", "CIO",
    "Chief Financial Officer", "CFO",
    "Chief Operating Officer", "COO",
    "Chief Marketing Officer", "CMO",
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
    "Vice President", "VP", "SVP", "EVP",
    "Director", "Senior Director",
]

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
        timeout: int = 30,
        max_retries: int = 3
    ):
        self._client_id = client_id or os.getenv("ZOOMINFO_CLIENT_ID")
        self._client_secret = client_secret or os.getenv("ZOOMINFO_CLIENT_SECRET")
        # Static token is stored as a fallback even in auto-auth mode so that
        # if OAuth2 fails we still have a working token instead of returning
        # empty results silently.
        self._static_token = access_token or os.getenv("ZOOMINFO_ACCESS_TOKEN")
        # Refresh token allows getting a new access token without a user login.
        # ZoomInfo's Okta app supports [authorization_code, refresh_token] grants —
        # client_credentials is NOT supported. A refresh token is obtained during
        # the initial authorization_code login flow and should be stored in
        # ZOOMINFO_REFRESH_TOKEN environment variable.
        self._refresh_token = os.getenv("ZOOMINFO_REFRESH_TOKEN")
        # Use token auto-refresh if either refresh_token or client credentials are set.
        self._auto_auth = bool(self._refresh_token or (self._client_id and self._client_secret))
        self._token_expires_at = 0.0

        if self._auto_auth:
            # Auto-auth mode: token will be refreshed on first request.
            # If auto-auth fails, falls back to the static token.
            self.access_token = None
        else:
            # Static token mode — use it directly
            self.access_token = self._static_token
            if not self.access_token:
                raise ValueError(
                    "ZoomInfo credentials required. Provide either "
                    "ZOOMINFO_REFRESH_TOKEN (recommended) or ZOOMINFO_ACCESS_TOKEN. "
                    "These values must be provided via environment variables."
                )

        self.base_url = ZOOMINFO_BASE_URL
        self.timeout = timeout
        self.max_retries = max_retries
        self.headers = {
            # Content-Type stays application/json — ZoomInfo accepts both
            # JSON:API and flat JSON request bodies with this type. Using
            # application/vnd.api+json breaks flat-format fallback payloads.
            # Accept must include application/vnd.api+json — ZoomInfo GTM sends
            # responses with that type and returns 406 if it's not accepted.
            "Content-Type": "application/json",
            "Accept": "application/vnd.api+json, application/json",
        }
        if self.access_token:
            self.headers["Authorization"] = f"Bearer {self.access_token}"
        self.rate_limiter = ZoomInfoRateLimiter()

    async def _authenticate(self) -> None:
        """
        Fetch a fresh access token from ZoomInfo's Okta endpoint.

        ZoomInfo's Okta application uses the authorization_code flow (user login)
        not client_credentials (machine-to-machine). Supported grant types are:
          [authorization_code, refresh_token]

        This method tries, in order:
          1. refresh_token grant (ZOOMINFO_REFRESH_TOKEN) — preferred for auto-refresh
          2. Falls back to static ZOOMINFO_ACCESS_TOKEN if refresh fails or is absent

        The client_credentials grant is NOT supported by ZoomInfo's Okta app,
        so ZOOMINFO_CLIENT_ID/SECRET alone cannot refresh the token automatically.
        """
        credentials = f"{self._client_id}:{self._client_secret}"
        basic_auth = base64.b64encode(credentials.encode()).decode()
        last_error: Optional[str] = None

        # Strategy 1: refresh_token grant — works when ZOOMINFO_REFRESH_TOKEN is set.
        # This is the correct long-term auto-refresh flow for ZoomInfo.
        if self._refresh_token:
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
                # Store the new refresh token if one was returned (rotation)
                if "refresh_token" in token_data:
                    self._refresh_token = token_data["refresh_token"]
                expires_in = token_data.get("expires_in", 3600)
                self._token_expires_at = time.time() + expires_in - 300
                self.headers["Authorization"] = f"Bearer {self.access_token}"
                logger.info("ZoomInfo token refreshed via refresh_token, expires in %ds", expires_in)
                return

            except httpx.HTTPStatusError as e:
                last_error = f"refresh_token grant failed: HTTP {e.response.status_code}"
                logger.warning(f"ZoomInfo refresh_token grant failed: {e.response.status_code}")
            except Exception as e:
                last_error = f"refresh_token grant exception: {e}"
                logger.warning(f"ZoomInfo refresh_token exception: {e}")

        # Strategy 2: Fall back to static token if available.
        # The static ZOOMINFO_ACCESS_TOKEN was obtained via the authorization_code
        # flow (user login). It expires (~1 hour) and must be manually refreshed
        # by the user if no ZOOMINFO_REFRESH_TOKEN is configured.
        if self._static_token:
            logger.warning(
                "ZoomInfo auto-refresh unavailable (%s). "
                "Using static ZOOMINFO_ACCESS_TOKEN — if this is expired, "
                "set ZOOMINFO_REFRESH_TOKEN in environment variables for automatic refresh.",
                last_error or "no refresh token configured"
            )
            self.access_token = self._static_token
            # We don't know when the static token expires — set a 24h window so
            # we don't retry auto-refresh on every request after the first failure.
            self._token_expires_at = time.time() + 86400
            self.headers["Authorization"] = f"Bearer {self.access_token}"
            return

        raise ValueError(
            "ZoomInfo token refresh failed. "
            "Set ZOOMINFO_REFRESH_TOKEN for automatic token refresh, or "
            "set ZOOMINFO_ACCESS_TOKEN with a fresh token from the ZoomInfo platform. "
            f"Last error: {last_error}"
        )

    async def _ensure_valid_token(self) -> None:
        """Re-authenticate if the current token is expired or missing."""
        if self._auto_auth and (
            not self.access_token or time.time() >= self._token_expires_at
        ):
            await self._authenticate()

    async def _make_request(
        self, endpoint: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make an authenticated POST request to ZoomInfo API."""
        await self._ensure_valid_token()
        await self.rate_limiter.acquire()
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"ZoomInfo POST {url}")
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url, json=payload, headers=self.headers
            )
            if not response.is_success:
                # Log full response body so the root cause is visible in logs
                try:
                    body = response.json()
                except Exception:
                    body = response.text[:500]
                logger.error(
                    f"ZoomInfo API error: {response.status_code} {response.reason_phrase} "
                    f"for {url} — body: {body}"
                )
                response.raise_for_status()
            # Handle 204 No Content (valid empty response)
            if response.status_code == 204 or not response.content:
                return {}
            return response.json()

    def _extract_data_list(self, response: Dict[str, Any]) -> list:
        """
        Extract the data list from a ZoomInfo API response.
        Handles multiple response formats:
          - {"data": [...]}              (JSON:API)
          - {"result": {"data": [...]}}  (legacy)
          - {"contacts": [...]}          (flat)
          - {"people": [...]}            (flat)
        """
        if "data" in response:
            return response["data"] if isinstance(response["data"], list) else []
        if "result" in response and isinstance(response["result"], dict):
            inner = response["result"]
            if "data" in inner:
                return inner["data"] if isinstance(inner["data"], list) else []
        for key in ("contacts", "people", "persons", "results", "items"):
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
    def _company_name_from_domain(domain: str) -> str:
        """Derive a best-guess company name from a domain (e.g. 'microsoft.com' → 'Microsoft')."""
        bare = domain.strip().rstrip("/")
        for prefix in ("https://www.", "http://www.", "https://", "http://", "www."):
            if bare.startswith(prefix):
                bare = bare[len(prefix):]
                break
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

        Returns:
            Dict with success, data (raw), normalized (standard fields), error
        """
        payload: Dict[str, Any] = {"data": {"type": "CompanyEnrich", "attributes": {}}}
        if domain:
            payload["data"]["attributes"]["companyWebsite"] = self._website_candidates(domain)
        if company_name:
            payload["data"]["attributes"]["companyName"] = company_name

        try:
            response = await self._make_request(
                ENDPOINTS["company_enrich"], payload
            )
            # Use _extract_data_list to handle all ZoomInfo response formats
            data_list = self._extract_data_list(response)
            if not data_list:
                return {"success": False, "data": {}, "normalized": {}, "error": "No company data found"}

            raw = data_list[0]
            normalized = self._normalize_company_data(raw)
            return {"success": True, "data": raw, "normalized": normalized, "error": None}

        except httpx.TimeoutException:
            logger.warning("ZoomInfo company enrich timed out")
            return {"success": False, "data": {}, "normalized": {}, "error": "Request timeout"}
        except httpx.HTTPStatusError as e:
            logger.warning(f"ZoomInfo company enrich HTTP error: {e.response.status_code}")
            return {"success": False, "data": {}, "normalized": {}, "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            logger.error(f"ZoomInfo company enrich failed: {e}")
            return {"success": False, "data": {}, "normalized": {}, "error": str(e)}

    async def search_contacts(
        self,
        domain: str,
        job_titles: Optional[List[str]] = None,
        max_results: int = 25
    ) -> Dict[str, Any]:
        """
        Search for executive and key contacts at a company.
        Uses multiple search strategies for maximum coverage:
        1. Management level search (C-Level, VP, Director, Manager)
        2. Broad job title keyword search as fallback

        Returns:
            Dict with success, people (normalized list), error
        """
        all_people = []
        seen_ids = set()
        last_error: Optional[str] = None

        # Build URL candidates once — comma-separated list covers all ZoomInfo URL formats.
        # ZoomInfo companyWebsite accepts comma-separated lists so we pass all variants
        # (https://www., https://, http://www., bare domain) in a single request to
        # maximise the chance of matching however ZoomInfo stores the company's website.
        website_candidates = self._website_candidates(domain)

        # Strategy 1: Search by management level.
        # ZoomInfo requires managementLevel as an array, not a string.
        # outputFields is intentionally omitted — it causes HTTP 400 on the search
        # endpoint. Phone data is retrieved via the separate contact enrich step.
        # Valid ZoomInfo GTM managementLevel enum values (hyphenated -Level suffix required)
        management_levels = ["C-Level", "VP-Level", "Director-Level", "Manager-Level"]
        for level in management_levels:
            # Try JSON:API wrapper format first, then flat format as fallback
            payloads_to_try = [
                # Format A: JSON:API wrapper (ZoomInfo GTM API format)
                {
                    "data": {
                        "type": "ContactSearch",
                        "attributes": {
                            "companyWebsite": website_candidates,
                            "managementLevel": [level],
                            "rpp": min(max_results, 10)
                        }
                    }
                },
                # Format B: flat JSON fallback (tries without wrapper if A fails)
                {
                    "companyWebsite": website_candidates,
                    "managementLevel": [level],
                    "maxResults": min(max_results, 10)
                },
            ]
            found_this_level = 0
            for fmt_payload in payloads_to_try:
                try:
                    response = await self._make_request(
                        ENDPOINTS["contact_search"], fmt_payload
                    )
                    data_list = self._extract_data_list(response)
                    if data_list:
                        for c in data_list:
                            person = self._normalize_contact(c)
                            pid = person.get("person_id") or person.get("email") or person.get("name")
                            if pid and pid not in seen_ids:
                                seen_ids.add(pid)
                                all_people.append(person)
                        found_this_level = len(data_list)
                        logger.info(f"ZoomInfo managementLevel=[{level}]: found {found_this_level} contacts")
                        break  # Success — no need to try next format
                    else:
                        logger.warning(
                            f"ZoomInfo managementLevel=[{level}] returned 0 contacts for domain={domain}. "
                            f"Response: {response}"
                        )
                except httpx.HTTPStatusError as e:
                    last_error = f"HTTP {e.response.status_code}"
                    logger.error(f"ZoomInfo managementLevel=[{level}] HTTP error: {e}")
                    continue  # Try next format (flat) before giving up on this level
                except Exception as e:
                    last_error = str(e)
                    logger.error(f"ZoomInfo managementLevel=[{level}] search failed: {e}")
                    continue  # Try next format before giving up

        # Strategy 2: Explicit job title search covering the full C-suite.
        # Uses CSUITE_JOB_TITLES (all chiefs, not just CEO/CTO/CIO/CFO/COO).
        if len(all_people) < max_results:
            if job_titles is None:
                job_titles = CSUITE_JOB_TITLES

            payloads_to_try = [
                {
                    "data": {
                        "type": "ContactSearch",
                        "attributes": {
                            "companyWebsite": website_candidates,
                            "jobTitle": job_titles,
                            "rpp": max_results
                        }
                    }
                },
                {
                    "companyWebsite": website_candidates,
                    "jobTitle": job_titles,
                    "maxResults": max_results
                },
            ]
            for fmt_payload in payloads_to_try:
                try:
                    response = await self._make_request(
                        ENDPOINTS["contact_search"], fmt_payload
                    )
                    data_list = self._extract_data_list(response)
                    if data_list:
                        for c in data_list:
                            person = self._normalize_contact(c)
                            pid = person.get("person_id") or person.get("email") or person.get("name")
                            if pid and pid not in seen_ids:
                                seen_ids.add(pid)
                                all_people.append(person)
                        logger.info(f"ZoomInfo jobTitle search: found {len(data_list)} additional contacts")
                        break
                    else:
                        logger.warning(
                            f"ZoomInfo jobTitle search returned 0 contacts for domain={domain}. "
                            f"Response: {response}"
                        )
                except httpx.HTTPStatusError as e:
                    last_error = f"HTTP {e.response.status_code}"
                    logger.error(f"ZoomInfo jobTitle search HTTP error: {e}")
                    continue  # Try flat format fallback
                except Exception as e:
                    last_error = str(e)
                    logger.error(f"ZoomInfo jobTitle search failed: {e}")
                    continue  # Try flat format fallback

        # Strategy 3: All URL variants, no filter — ensures we always try the broadest
        # possible companyWebsite query with all URL format candidates.
        if not all_people:
            try:
                response = await self._make_request(
                    ENDPOINTS["contact_search"],
                    {"data": {"type": "ContactSearch", "attributes": {
                        "companyWebsite": website_candidates,
                        "rpp": max_results,
                    }}}
                )
                data_list = self._extract_data_list(response)
                for c in data_list:
                    person = self._normalize_contact(c)
                    pid = person.get("person_id") or person.get("email") or person.get("name")
                    if pid and pid not in seen_ids:
                        seen_ids.add(pid)
                        all_people.append(person)
                if all_people:
                    logger.info(f"ZoomInfo multi-URL fallback: found {len(all_people)} contacts for domain={domain}")
                else:
                    logger.warning(
                        f"ZoomInfo multi-URL fallback returned 0 contacts for domain={domain}. "
                        f"website_candidates={website_candidates}"
                    )
            except Exception as e:
                logger.warning(f"ZoomInfo multi-URL fallback failed: {e}")

        # Strategy 4: Company name fallback — derive company name from domain and search by
        # companyName. ZoomInfo stores company names separately from website URLs, so this
        # may match when the website-based search fails.
        if not all_people:
            company_name = self._company_name_from_domain(domain)
            if company_name:
                try:
                    response = await self._make_request(
                        ENDPOINTS["contact_search"],
                        {"data": {"type": "ContactSearch", "attributes": {
                            "companyName": company_name,
                            "rpp": max_results,
                        }}}
                    )
                    data_list = self._extract_data_list(response)
                    for c in data_list:
                        person = self._normalize_contact(c)
                        pid = person.get("person_id") or person.get("email") or person.get("name")
                        if pid and pid not in seen_ids:
                            seen_ids.add(pid)
                            all_people.append(person)
                    if all_people:
                        logger.info(f"ZoomInfo companyName fallback: found {len(all_people)} contacts for name={company_name}")
                    else:
                        logger.warning(f"ZoomInfo companyName fallback also returned 0 contacts for name={company_name}")
                except Exception as e:
                    logger.warning(f"ZoomInfo companyName fallback failed: {e}")

        logger.info(f"ZoomInfo total contacts found: {len(all_people)} for domain={domain}")
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

        Returns:
            Dict with success, people (enriched normalized list), error
        """
        if not person_ids:
            return {"success": True, "people": [], "error": None}

        payload: Dict[str, Any] = {
            "data": {
                "type": "ContactEnrich",
                "attributes": {
                    "personId": person_ids
                }
            }
        }

        try:
            response = await self._make_request(
                ENDPOINTS["contact_enrich"], payload
            )
            data_list = response.get("data", [])
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

    async def enrich_intent(self, domain: str) -> Dict[str, Any]:
        """
        Get buyer intent signals for a company with full field extraction.

        Returns:
            Dict with success, intent_signals (normalized list), raw_data, error
        """
        # ZoomInfo Intent Enrich requires: company identifier + at least 1 topic.
        # We use DEFAULT_INTENT_TOPICS (broad B2B topics) so we capture all
        # relevant intent signals regardless of the company's specific focus.
        payload: Dict[str, Any] = {
            "data": {
                "type": "IntentEnrich",
                "attributes": {
                    "companyWebsite": self._website_candidates(domain),
                    "topic": DEFAULT_INTENT_TOPICS,
                }
            }
        }

        try:
            response = await self._make_request(
                ENDPOINTS["intent_enrich"], payload
            )
            raw_signals = response.get("data", [])
            # Normalize each intent signal to extract all fields
            normalized_signals = [self._normalize_intent_signal(sig) for sig in raw_signals]
            return {
                "success": True,
                "intent_signals": normalized_signals,
                "raw_data": raw_signals,
                "error": None
            }

        except httpx.TimeoutException:
            return {"success": False, "intent_signals": [], "raw_data": [], "error": "Request timeout"}
        except httpx.HTTPStatusError as e:
            return {"success": False, "intent_signals": [], "raw_data": [], "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            logger.error(f"ZoomInfo intent enrich failed: {e}")
            return {"success": False, "intent_signals": [], "raw_data": [], "error": str(e)}

    async def search_scoops(
        self, domain: str, scoop_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Search for business scoops/events at a company with full field extraction.

        Returns:
            Dict with success, scoops (normalized list), raw_data, error
        """
        payload: Dict[str, Any] = {
            "data": {
                "type": "ScoopSearch",
                "attributes": {
                    "companyWebsite": self._website_candidates(domain)
                }
            }
        }
        if scoop_types:
            payload["data"]["attributes"]["scoopTypes"] = scoop_types

        try:
            response = await self._make_request(
                ENDPOINTS["scoops_search"], payload
            )
            raw_scoops = response.get("data", [])
            # Normalize each scoop to extract all fields
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
            return {"success": False, "scoops": [], "raw_data": [], "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            logger.error(f"ZoomInfo scoops search failed: {e}")
            return {"success": False, "scoops": [], "raw_data": [], "error": str(e)}

    async def search_news(self, company_name: str) -> Dict[str, Any]:
        """
        Search for company news articles with full field extraction.

        Returns:
            Dict with success, articles (normalized list), raw_data, error
        """
        payload: Dict[str, Any] = {
            "data": {
                "type": "NewsSearch",
                "attributes": {
                    "companyName": company_name
                }
            }
        }

        try:
            response = await self._make_request(
                ENDPOINTS["news_search"], payload
            )
            raw_articles = response.get("data", [])
            # Normalize each article to extract all fields
            normalized_articles = [self._normalize_news_article(article) for article in raw_articles]
            return {
                "success": True,
                "articles": normalized_articles,
                "raw_data": raw_articles,
                "error": None
            }

        except httpx.TimeoutException:
            return {"success": False, "articles": [], "raw_data": [], "error": "Request timeout"}
        except httpx.HTTPStatusError as e:
            return {"success": False, "articles": [], "raw_data": [], "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            logger.error(f"ZoomInfo news search failed: {e}")
            return {"success": False, "articles": [], "raw_data": [], "error": str(e)}

    async def enrich_technologies(self, domain: str) -> Dict[str, Any]:
        """
        Get installed technologies for a company with full field extraction.

        Returns:
            Dict with success, technologies (normalized list), raw_data, error
        """
        payload: Dict[str, Any] = {
            "data": {
                "type": "TechnologyEnrich",
                "attributes": {
                    "companyWebsite": self._website_candidates(domain)
                }
            }
        }

        try:
            response = await self._make_request(
                ENDPOINTS["tech_enrich"], payload
            )
            raw_technologies = response.get("data", [])
            # Normalize each technology to extract all fields
            normalized_technologies = [self._normalize_technology(tech) for tech in raw_technologies]
            return {
                "success": True,
                "technologies": normalized_technologies,
                "raw_data": raw_technologies,
                "error": None
            }

        except httpx.TimeoutException:
            return {"success": False, "technologies": [], "raw_data": [], "error": "Request timeout"}
        except httpx.HTTPStatusError as e:
            return {"success": False, "technologies": [], "raw_data": [], "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            logger.error(f"ZoomInfo tech enrich failed: {e}")
            return {"success": False, "technologies": [], "raw_data": [], "error": str(e)}

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
            "company_id": attrs.get("companyId", attrs.get("id", raw.get("id", ""))),
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
