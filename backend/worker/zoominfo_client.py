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
        self._auto_auth = bool(self._client_id and self._client_secret)
        self._token_expires_at = 0.0

        if self._auto_auth:
            # Auto-auth mode: token will be fetched on first request
            self.access_token = None
        else:
            # Static token mode
            self.access_token = access_token or os.getenv("ZOOMINFO_ACCESS_TOKEN")
            if not self.access_token:
                raise ValueError(
                    "ZoomInfo credentials required. Provide either "
                    "client_id + client_secret (recommended) or access_token. "
                    "These values must be provided via environment variables."
                )

        self.base_url = ZOOMINFO_BASE_URL
        self.timeout = timeout
        self.max_retries = max_retries
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.access_token:
            self.headers["Authorization"] = f"Bearer {self.access_token}"
        self.rate_limiter = ZoomInfoRateLimiter()

    async def _authenticate(self) -> None:
        """Fetch a fresh access token using client_credentials grant."""
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
                    data="grant_type=client_credentials&scope=openid",
                )
                response.raise_for_status()
                token_data = response.json()

            self.access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)
            # Refresh 5 minutes early to avoid edge-case expiry
            self._token_expires_at = time.time() + expires_in - 300
            self.headers["Authorization"] = f"Bearer {self.access_token}"
            logger.info("ZoomInfo token refreshed, expires in %ds", expires_in)

        except httpx.HTTPStatusError as e:
            raise ValueError(
                f"ZoomInfo authentication failed: HTTP {e.response.status_code}. "
                "Check client_id and client_secret."
            )
        except Exception as e:
            raise ValueError(f"ZoomInfo authentication failed: {e}")

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
            payload["data"]["attributes"]["companyDomain"] = domain
        if company_name:
            payload["data"]["attributes"]["companyName"] = company_name

        try:
            response = await self._make_request(
                ENDPOINTS["company_enrich"], payload
            )
            data_list = response.get("data", [])
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

        # Strategy 1: Search by management level.
        # ZoomInfo requires managementLevel as an array, not a string.
        management_levels = ["C-Level", "VP-Level", "Director", "Manager"]
        for level in management_levels:
            # Try JSON:API wrapper format first, then flat format as fallback
            payloads_to_try = [
                # Format A: JSON:API wrapper (current ZoomInfo GTM format)
                {
                    "data": {
                        "type": "ContactSearch",
                        "attributes": {
                            "companyDomain": domain,
                            "managementLevel": [level],
                            "pageSize": min(max_results, 10)
                        }
                    }
                },
                # Format B: flat JSON (ZoomInfo Enrich API / legacy format)
                {
                    "companyDomain": domain,
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
                    break  # HTTP error — no point retrying different format
                except Exception as e:
                    last_error = str(e)
                    logger.error(f"ZoomInfo managementLevel=[{level}] search failed: {e}")
                    break

        # Strategy 2: Explicit job title search for CTO/CIO/CFO/COO and senior roles.
        if len(all_people) < max_results:
            if job_titles is None:
                job_titles = [
                    "Chief Technology Officer", "CTO",
                    "Chief Information Officer", "CIO",
                    "Chief Financial Officer", "CFO",
                    "Chief Operating Officer", "COO",
                    "Chief Executive Officer", "CEO",
                    "Chief Information Security Officer", "CISO",
                    "Vice President", "VP", "SVP", "EVP",
                    "Director", "Senior Director",
                ]

            payloads_to_try = [
                {
                    "data": {
                        "type": "ContactSearch",
                        "attributes": {
                            "companyDomain": domain,
                            "jobTitle": job_titles,
                            "pageSize": max_results
                        }
                    }
                },
                {
                    "companyDomain": domain,
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
                    break
                except Exception as e:
                    last_error = str(e)
                    logger.error(f"ZoomInfo jobTitle search failed: {e}")
                    break

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

    async def enrich_intent(self, domain: str) -> Dict[str, Any]:
        """
        Get buyer intent signals for a company with full field extraction.

        Returns:
            Dict with success, intent_signals (normalized list), raw_data, error
        """
        payload: Dict[str, Any] = {
            "data": {
                "type": "IntentEnrich",
                "attributes": {
                    "companyDomain": domain
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
                    "companyDomain": domain
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
                    "companyDomain": domain
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
