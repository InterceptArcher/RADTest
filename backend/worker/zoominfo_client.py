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
            "Content-Type": "application/vnd.api+json",
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
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url, json=payload, headers=self.headers
            )
            response.raise_for_status()
            return response.json()

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
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Search for executive contacts at a company.

        Returns:
            Dict with success, people (normalized list), error
        """
        if job_titles is None:
            job_titles = ["CEO", "CTO", "CFO", "CIO", "CISO", "COO", "CPO",
                          "President", "VP"]

        payload: Dict[str, Any] = {
            "data": {
                "type": "ContactSearch",
                "attributes": {
                    "companyDomain": domain,
                    "jobTitle": job_titles,
                    "pageSize": max_results
                }
            }
        }

        try:
            response = await self._make_request(
                ENDPOINTS["contact_search"], payload
            )
            data_list = response.get("data", [])
            people = [self._normalize_contact(c) for c in data_list]
            return {"success": True, "people": people, "error": None}

        except httpx.TimeoutException:
            logger.warning("ZoomInfo contact search timed out")
            return {"success": False, "people": [], "error": "Request timeout"}
        except httpx.HTTPStatusError as e:
            logger.warning(f"ZoomInfo contact search HTTP error: {e.response.status_code}")
            return {"success": False, "people": [], "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            logger.error(f"ZoomInfo contact search failed: {e}")
            return {"success": False, "people": [], "error": str(e)}

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
        max_results: int = 10
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
        """
        return {
            # Identification
            "scoop_id": raw.get("scoopId", raw.get("id", "")),
            "scoop_type": raw.get("scoopType", raw.get("type", "")),
            "title": raw.get("title", raw.get("headline", "")),

            # Content
            "description": raw.get("description", raw.get("summary", "")),
            "full_text": raw.get("fullText", raw.get("body", "")),
            "snippet": raw.get("snippet", ""),

            # Temporal
            "date": raw.get("date", raw.get("publishedDate", "")),
            "published_date": raw.get("publishedDate", raw.get("date", "")),
            "discovered_date": raw.get("discoveredDate", ""),
            "last_updated": raw.get("lastUpdated", ""),

            # Source
            "source": raw.get("source", ""),
            "source_url": raw.get("sourceUrl", raw.get("url", "")),
            "author": raw.get("author", ""),

            # Classification
            "category": raw.get("category", ""),
            "tags": raw.get("tags", []),
            "keywords": raw.get("keywords", []),

            # Impact & relevance
            "relevance_score": raw.get("relevanceScore", 0),
            "importance": raw.get("importance", ""),
            "sentiment": raw.get("sentiment", ""),

            # Additional details (type-specific)
            "amount": raw.get("amount", ""),  # for funding
            "investors": raw.get("investors", []),  # for funding
            "person_name": raw.get("personName", ""),  # for new hires
            "person_title": raw.get("personTitle", ""),  # for new hires
            "location": raw.get("location", ""),  # for expansions
            "partner_name": raw.get("partnerName", ""),  # for partnerships
        }

    @staticmethod
    def _normalize_news_article(raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize ZoomInfo news article to extract ALL fields.
        """
        return {
            # Identification
            "article_id": raw.get("articleId", raw.get("id", "")),
            "title": raw.get("title", raw.get("headline", "")),

            # Content
            "description": raw.get("description", raw.get("summary", "")),
            "full_text": raw.get("fullText", raw.get("body", raw.get("content", ""))),
            "snippet": raw.get("snippet", ""),
            "excerpt": raw.get("excerpt", ""),

            # Source
            "source": raw.get("source", raw.get("publisher", "")),
            "url": raw.get("url", raw.get("sourceUrl", "")),
            "author": raw.get("author", ""),
            "source_domain": raw.get("sourceDomain", ""),

            # Temporal
            "published_date": raw.get("publishedDate", raw.get("date", "")),
            "discovered_date": raw.get("discoveredDate", ""),
            "last_updated": raw.get("lastUpdated", ""),

            # Classification
            "category": raw.get("category", ""),
            "subcategory": raw.get("subcategory", ""),
            "tags": raw.get("tags", []),
            "keywords": raw.get("keywords", []),
            "topics": raw.get("topics", []),

            # Engagement & impact
            "relevance_score": raw.get("relevanceScore", 0),
            "sentiment": raw.get("sentiment", ""),
            "sentiment_score": raw.get("sentimentScore", 0),
            "language": raw.get("language", "en"),

            # Media
            "image_url": raw.get("imageUrl", raw.get("thumbnailUrl", "")),
            "video_url": raw.get("videoUrl", ""),
        }

    @staticmethod
    def _normalize_technology(raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize ZoomInfo technology installation data to extract ALL fields.
        """
        return {
            # Technology identification
            "tech_id": raw.get("technologyId", raw.get("id", "")),
            "tech_name": raw.get("technologyName", raw.get("name", raw.get("technology", ""))),
            "product_name": raw.get("productName", ""),
            "vendor": raw.get("vendor", raw.get("vendorName", "")),

            # Classification
            "category": raw.get("category", ""),
            "subcategory": raw.get("subcategory", ""),
            "tech_type": raw.get("technologyType", raw.get("type", "")),
            "tags": raw.get("tags", []),

            # Installation details
            "install_date": raw.get("installDate", raw.get("installedDate", "")),
            "first_seen": raw.get("firstSeen", ""),
            "last_seen": raw.get("lastSeen", ""),
            "status": raw.get("status", "active"),  # active, inactive, unknown

            # Usage & adoption
            "adoption_level": raw.get("adoptionLevel", ""),  # enterprise-wide, departmental, etc.
            "usage_frequency": raw.get("usageFrequency", ""),
            "user_count": raw.get("userCount", 0),
            "license_count": raw.get("licenseCount", 0),

            # Technical details
            "version": raw.get("version", ""),
            "deployment_type": raw.get("deploymentType", ""),  # cloud, on-premise, hybrid
            "integration_points": raw.get("integrationPoints", []),

            # Confidence & quality
            "confidence_score": raw.get("confidenceScore", 0),
            "data_source": raw.get("dataSource", ""),
            "last_verified": raw.get("lastVerified", ""),
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
            "topic_id": raw.get("topicId", raw.get("id", "")),
            "topic": raw.get("topicName", raw.get("topic", raw.get("name", ""))),
            "topic_name": raw.get("topicName", raw.get("topic", "")),

            # Scoring metrics
            "intent_score": raw.get("intentScore", raw.get("score", 0)),
            "score": raw.get("intentScore", raw.get("score", 0)),
            "audience_strength": raw.get("audienceStrength", raw.get("strength", "")),
            "engagement_score": raw.get("engagementScore", 0),
            "activity_level": raw.get("activityLevel", ""),

            # Context and classification
            "description": raw.get("description", ""),
            "category": raw.get("category", ""),
            "subcategory": raw.get("subcategory", ""),
            "keywords": raw.get("keywords", []),
            "topic_type": raw.get("topicType", raw.get("type", "")),

            # Temporal information
            "last_seen": raw.get("lastSeen", raw.get("lastSeenDate", "")),
            "first_seen": raw.get("firstSeen", raw.get("firstSeenDate", "")),
            "timestamp": raw.get("timestamp", ""),
            "duration_days": raw.get("durationDays", 0),

            # Additional metrics
            "research_count": raw.get("researchCount", 0),
            "page_views": raw.get("pageViews", 0),
            "unique_visitors": raw.get("uniqueVisitors", 0),
            "trend": raw.get("trend", ""),  # increasing, stable, decreasing

            # Confidence and quality
            "confidence": raw.get("confidence", raw.get("confidenceScore", 0)),
            "data_quality": raw.get("dataQuality", ""),
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
        """
        # Location data
        city = raw.get("city", "")
        state = raw.get("state", "")
        country = raw.get("country", "")
        headquarters = ", ".join(filter(None, [city, state, country]))

        # Full address if available
        street = raw.get("street", raw.get("address", ""))
        zip_code = raw.get("zipCode", raw.get("zip", ""))
        full_address = ", ".join(filter(None, [street, city, state, zip_code, country]))

        return {
            # Basic identification
            "company_name": raw.get("companyName", ""),
            "domain": raw.get("domain", raw.get("website", "")),
            "company_type": raw.get("companyType", raw.get("type", "")),
            "description": raw.get("description", raw.get("companyDescription", "")),

            # Financial data
            "employee_count": raw.get("employeeCount", raw.get("employees", "")),
            "employees_range": raw.get("employeesRange", raw.get("employeeRange", "")),
            "revenue": raw.get("revenue", raw.get("revenueUSD", "")),
            "revenue_range": raw.get("revenueRange", ""),
            "estimated_revenue": raw.get("estimatedRevenue", ""),

            # Industry classification
            "industry": raw.get("industry", raw.get("primaryIndustry", "")),
            "sub_industry": raw.get("subIndustry", raw.get("secondaryIndustry", "")),
            "industry_category": raw.get("industryCategory", ""),
            "sic_codes": raw.get("sicCodes", raw.get("sic", [])),
            "naics_codes": raw.get("naicsCodes", raw.get("naics", [])),

            # Location
            "headquarters": headquarters,
            "full_address": full_address,
            "street": street,
            "city": city,
            "state": state,
            "zip_code": zip_code,
            "country": country,
            "metro_area": raw.get("metroArea", ""),

            # Contact information
            "phone": raw.get("phone", raw.get("phoneNumber", "")),
            "fax": raw.get("fax", raw.get("faxNumber", "")),
            "corporate_email": raw.get("email", raw.get("corporateEmail", "")),

            # Social media & web presence
            "linkedin_url": raw.get("linkedInUrl", raw.get("linkedinUrl", raw.get("linkedin", ""))),
            "facebook_url": raw.get("facebookUrl", raw.get("facebook", "")),
            "twitter_url": raw.get("twitterUrl", raw.get("twitter", "")),
            "website": raw.get("website", raw.get("websiteUrl", "")),

            # Leadership
            "ceo": raw.get("ceoName", raw.get("ceo", "")),
            "cfo": raw.get("cfoName", raw.get("cfo", "")),
            "cto": raw.get("ctoName", raw.get("cto", "")),
            "executives": raw.get("executives", []),

            # Organizational details
            "founded_year": raw.get("yearFounded", raw.get("foundedYear", "")),
            "ticker": raw.get("ticker", raw.get("tickerSymbol", "")),
            "stock_exchange": raw.get("stockExchange", ""),
            "parent_company": raw.get("parentCompany", ""),
            "ownership_type": raw.get("ownershipType", raw.get("ownership", "")),

            # Additional firmographic data
            "company_size": raw.get("companySize", ""),
            "fiscal_year_end": raw.get("fiscalYearEnd", ""),
            "legal_name": raw.get("legalName", ""),
            "dba_name": raw.get("dbaName", raw.get("doingBusinessAs", "")),
            "former_names": raw.get("formerNames", []),

            # Technology & operations
            "technologies": raw.get("technologies", []),
            "tech_install_count": raw.get("techInstallCount", 0),
            "alexa_rank": raw.get("alexaRank", ""),
            "fortune_rank": raw.get("fortuneRank", ""),

            # Growth metrics
            "one_year_employee_growth": raw.get("oneYearEmployeeGrowthRate", ""),
            "two_year_employee_growth": raw.get("twoYearEmployeeGrowthRate", ""),
            "funding_amount": raw.get("fundingAmount", ""),
            "fortune_rank": raw.get("fortuneRank", ""),
            "business_model": raw.get("businessModel", ""),
            "num_locations": raw.get("numLocations", ""),

            # Additional metadata
            "company_id": raw.get("companyId", raw.get("id", "")),
            "logo_url": raw.get("logoUrl", raw.get("logo", "")),
            "last_updated": raw.get("lastUpdated", ""),
            "data_quality_score": raw.get("dataQualityScore", raw.get("confidenceScore", "")),
        }

    @staticmethod
    def _normalize_contact(raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize ZoomInfo contact with full profile data.

        Includes phone numbers (direct, mobile, company), accuracy scores,
        department, and management level from Contact Enrich endpoint.
        """
        first_name = raw.get("firstName", "")
        last_name = raw.get("lastName", "")
        name = f"{first_name} {last_name}".strip()

        return {
            "name": name,
            "title": raw.get("jobTitle", ""),
            "email": raw.get("email", ""),
            "phone": raw.get("phone", ""),
            "linkedin": raw.get("linkedInUrl", ""),
            "direct_phone": raw.get("directPhone", ""),
            "mobile_phone": raw.get("mobilePhone", ""),
            "company_phone": raw.get("companyPhone", ""),
            "contact_accuracy_score": raw.get("contactAccuracyScore", 0),
            "department": raw.get("department", ""),
            "management_level": raw.get("managementLevel", ""),
            "person_id": raw.get("personId", raw.get("id", "")),
        }
