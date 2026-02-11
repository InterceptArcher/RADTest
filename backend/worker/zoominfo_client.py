"""
ZoomInfo API client for company enrichment, contact search,
intent signals, scoops, news, and technology data.

All requests use Bearer token authentication.
The access token must be provided via environment variables.
"""
import asyncio
import logging
import os
import time
from typing import Dict, Any, List, Optional

import httpx

logger = logging.getLogger(__name__)

ZOOMINFO_BASE_URL = "https://api.zoominfo.com/gtm"

ENDPOINTS = {
    "company_enrich": "/data/v1/companies/enrich",
    "contact_search": "/data/v1/contacts/search",
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
        timeout: int = 30,
        max_retries: int = 3
    ):
        self.access_token = access_token or os.getenv("ZOOMINFO_ACCESS_TOKEN")
        if not self.access_token:
            raise ValueError(
                "ZOOMINFO_ACCESS_TOKEN is required. "
                "This value must be provided via environment variables."
            )
        self.base_url = ZOOMINFO_BASE_URL
        self.timeout = timeout
        self.max_retries = max_retries
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/vnd.api+json",
            "Accept": "application/json"
        }
        self.rate_limiter = ZoomInfoRateLimiter()

    async def _make_request(
        self, endpoint: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make an authenticated POST request to ZoomInfo API."""
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

    async def enrich_intent(self, domain: str) -> Dict[str, Any]:
        """
        Get buyer intent signals for a company.

        Returns:
            Dict with success, intent_signals (list), error
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
            signals = response.get("data", [])
            return {"success": True, "intent_signals": signals, "error": None}

        except httpx.TimeoutException:
            return {"success": False, "intent_signals": [], "error": "Request timeout"}
        except httpx.HTTPStatusError as e:
            return {"success": False, "intent_signals": [], "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            logger.error(f"ZoomInfo intent enrich failed: {e}")
            return {"success": False, "intent_signals": [], "error": str(e)}

    async def search_scoops(
        self, domain: str, scoop_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Search for business scoops/events at a company.

        Returns:
            Dict with success, scoops (list), error
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
            scoops = response.get("data", [])
            return {"success": True, "scoops": scoops, "error": None}

        except httpx.TimeoutException:
            return {"success": False, "scoops": [], "error": "Request timeout"}
        except httpx.HTTPStatusError as e:
            return {"success": False, "scoops": [], "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            logger.error(f"ZoomInfo scoops search failed: {e}")
            return {"success": False, "scoops": [], "error": str(e)}

    async def search_news(self, company_name: str) -> Dict[str, Any]:
        """
        Search for company news articles.

        Returns:
            Dict with success, articles (list), error
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
            articles = response.get("data", [])
            return {"success": True, "articles": articles, "error": None}

        except httpx.TimeoutException:
            return {"success": False, "articles": [], "error": "Request timeout"}
        except httpx.HTTPStatusError as e:
            return {"success": False, "articles": [], "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            logger.error(f"ZoomInfo news search failed: {e}")
            return {"success": False, "articles": [], "error": str(e)}

    async def enrich_technologies(self, domain: str) -> Dict[str, Any]:
        """
        Get installed technologies for a company.

        Returns:
            Dict with success, technologies (list), error
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
            technologies = response.get("data", [])
            return {"success": True, "technologies": technologies, "error": None}

        except httpx.TimeoutException:
            return {"success": False, "technologies": [], "error": "Request timeout"}
        except httpx.HTTPStatusError as e:
            return {"success": False, "technologies": [], "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            logger.error(f"ZoomInfo tech enrich failed: {e}")
            return {"success": False, "technologies": [], "error": str(e)}

    @staticmethod
    def _normalize_company_data(raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize ZoomInfo fields to the common schema used by Apollo/PDL.

        Mapping:
          companyName    -> company_name
          employeeCount  -> employee_count
          revenue        -> revenue
          industry       -> industry
          city+state     -> headquarters
          yearFounded    -> founded_year
          ceoName        -> ceo
        """
        city = raw.get("city", "")
        state = raw.get("state", "")
        headquarters = ", ".join(filter(None, [city, state]))

        return {
            "company_name": raw.get("companyName", ""),
            "employee_count": raw.get("employeeCount"),
            "revenue": raw.get("revenue"),
            "industry": raw.get("industry", ""),
            "headquarters": headquarters,
            "founded_year": raw.get("yearFounded"),
            "ceo": raw.get("ceoName", ""),
            "domain": raw.get("domain", ""),
            "country": raw.get("country", ""),
        }

    @staticmethod
    def _normalize_contact(raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize ZoomInfo contact to match Apollo/PDL stakeholder format.

        Mapping:
          firstName+lastName -> name
          jobTitle           -> title
          email              -> email
          phone              -> phone
          linkedInUrl        -> linkedin
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
        }
