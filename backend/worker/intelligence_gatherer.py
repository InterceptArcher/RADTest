"""
Parallelized intelligence gathering worker.
Executes asynchronous requests to Apollo.io, PeopleDataLabs, and ZoomInfo.
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import httpx

logger = logging.getLogger(__name__)


class DataSource(Enum):
    """Supported data sources for intelligence gathering."""
    APOLLO = "apollo"
    PDL = "peopledatalabs"
    ZOOMINFO = "zoominfo"


@dataclass
class IntelligenceResult:
    """Result from an intelligence gathering operation."""
    source: DataSource
    success: bool
    data: Optional[Dict[str, Any]]
    error: Optional[str]
    attempt_count: int


class CircuitBreaker:
    """
    Circuit breaker pattern implementation to prevent overwhelming external services.
    """

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting to close circuit
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half-open

    def can_execute(self) -> bool:
        """Check if execution is allowed based on circuit state."""
        import time

        if self.state == "closed":
            return True

        if self.state == "open":
            if self.last_failure_time and \
               (time.time() - self.last_failure_time) > self.timeout:
                self.state = "half-open"
                return True
            return False

        # half-open state
        return True

    def record_success(self):
        """Record a successful execution."""
        self.failure_count = 0
        self.state = "closed"

    def record_failure(self):
        """Record a failed execution."""
        import time

        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures"
            )


class IntelligenceGatherer:
    """
    Handles parallelized intelligence gathering from multiple sources.

    Features:
    - Asynchronous high-throughput requests
    - Retry mechanism with exponential backoff
    - Circuit breaker pattern
    - Rate limiting support
    """

    def __init__(
        self,
        apollo_api_key: str,
        pdl_api_key: str,
        zoominfo_access_token: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = 30
    ):
        """
        Initialize intelligence gatherer.

        Args:
            apollo_api_key: Apollo.io API key (from environment)
            pdl_api_key: PeopleDataLabs API key (from environment)
            zoominfo_access_token: ZoomInfo access token (optional, from environment)
            max_retries: Maximum retry attempts per request
            timeout: Request timeout in seconds
        """
        self.apollo_api_key = apollo_api_key
        self.pdl_api_key = pdl_api_key
        self.zoominfo_access_token = zoominfo_access_token
        self.max_retries = max_retries
        self.timeout = timeout

        # Circuit breakers for each service
        self.circuit_breakers = {
            DataSource.APOLLO: CircuitBreaker(),
            DataSource.PDL: CircuitBreaker(),
            DataSource.ZOOMINFO: CircuitBreaker()
        }

        # Initialize ZoomInfo client if token provided
        self.zoominfo_client = None
        if zoominfo_access_token:
            try:
                from zoominfo_client import ZoomInfoClient
                self.zoominfo_client = ZoomInfoClient(
                    access_token=zoominfo_access_token,
                    timeout=timeout,
                    max_retries=max_retries
                )
                logger.info("ZoomInfo client initialized successfully")
            except Exception as e:
                logger.warning(f"ZoomInfo client could not be initialized: {e}")

    async def gather_company_intelligence(
        self,
        company_name: str,
        domain: str,
        sources: Optional[List[DataSource]] = None,
        include_people: bool = True
    ) -> List[IntelligenceResult]:
        """
        Gather intelligence from multiple sources in parallel.

        Args:
            company_name: Name of the company
            domain: Company domain
            sources: List of sources to query (defaults to all)
            include_people: Whether to fetch executive/people data

        Returns:
            List of IntelligenceResult objects
        """
        if sources is None:
            sources = [DataSource.APOLLO, DataSource.PDL]
            if self.zoominfo_access_token:
                sources.append(DataSource.ZOOMINFO)

        logger.info(
            f"Starting intelligence gathering for {company_name} "
            f"from {len(sources)} sources (include_people={include_people})"
        )

        # Create tasks for parallel execution
        tasks = []
        for source in sources:
            if source == DataSource.APOLLO:
                tasks.append(self._fetch_apollo_data(company_name, domain))
                if include_people:
                    tasks.append(self._fetch_apollo_people(company_name, domain))
            elif source == DataSource.PDL:
                tasks.append(self._fetch_pdl_data(company_name, domain))
                if include_people:
                    tasks.append(self._fetch_pdl_people(company_name, domain))
            elif source == DataSource.ZOOMINFO:
                if self.zoominfo_client:
                    tasks.append(self._fetch_zoominfo_data(company_name, domain))
                    if include_people:
                        tasks.append(self._fetch_zoominfo_people(company_name, domain))

        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        intelligence_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Task failed with exception: {result}")
            else:
                intelligence_results.append(result)

        logger.info(
            f"Intelligence gathering complete. "
            f"{len(intelligence_results)} results collected"
        )

        return intelligence_results

    async def _fetch_apollo_data(
        self,
        company_name: str,
        domain: str
    ) -> IntelligenceResult:
        """
        Fetch data from Apollo.io with retry and circuit breaker.

        Args:
            company_name: Name of the company
            domain: Company domain

        Returns:
            IntelligenceResult with Apollo data
        """
        source = DataSource.APOLLO
        circuit_breaker = self.circuit_breakers[source]

        # Check circuit breaker
        if not circuit_breaker.can_execute():
            logger.warning(f"Circuit breaker open for {source.value}")
            return IntelligenceResult(
                source=source,
                success=False,
                data=None,
                error="Circuit breaker open",
                attempt_count=0
            )

        # Retry logic with exponential backoff
        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        "https://api.apollo.io/v1/organizations/enrich",
                        json={
                            "domain": domain,
                            "name": company_name
                        },
                        headers={
                            "Content-Type": "application/json",
                            "X-Api-Key": self.apollo_api_key
                        }
                    )

                    response.raise_for_status()
                    data = response.json()

                    circuit_breaker.record_success()

                    logger.info(
                        f"Successfully fetched Apollo data for {company_name}"
                    )

                    return IntelligenceResult(
                        source=source,
                        success=True,
                        data=data,
                        error=None,
                        attempt_count=attempt
                    )

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    # Rate limit hit
                    logger.warning(
                        f"Rate limit hit for Apollo (attempt {attempt})"
                    )
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    logger.error(f"HTTP error from Apollo: {e}")
                    circuit_breaker.record_failure()
                    break

            except (httpx.TimeoutException, httpx.RequestError) as e:
                logger.warning(
                    f"Network error with Apollo (attempt {attempt}): {e}"
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                circuit_breaker.record_failure()

            except Exception as e:
                logger.error(f"Unexpected error with Apollo: {e}")
                circuit_breaker.record_failure()
                break

        return IntelligenceResult(
            source=source,
            success=False,
            data=None,
            error="Failed after retries",
            attempt_count=self.max_retries
        )

    async def _fetch_pdl_data(
        self,
        company_name: str,
        domain: str
    ) -> IntelligenceResult:
        """
        Fetch data from PeopleDataLabs with retry and circuit breaker.

        Args:
            company_name: Name of the company
            domain: Company domain

        Returns:
            IntelligenceResult with PDL data
        """
        source = DataSource.PDL
        circuit_breaker = self.circuit_breakers[source]

        # Check circuit breaker
        if not circuit_breaker.can_execute():
            logger.warning(f"Circuit breaker open for {source.value}")
            return IntelligenceResult(
                source=source,
                success=False,
                data=None,
                error="Circuit breaker open",
                attempt_count=0
            )

        # Retry logic with exponential backoff
        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(
                        "https://api.peopledatalabs.com/v5/company/enrich",
                        params={
                            "website": domain,
                            "name": company_name
                        },
                        headers={
                            "X-Api-Key": self.pdl_api_key
                        }
                    )

                    response.raise_for_status()
                    data = response.json()

                    circuit_breaker.record_success()

                    logger.info(
                        f"Successfully fetched PDL data for {company_name}"
                    )

                    return IntelligenceResult(
                        source=source,
                        success=True,
                        data=data,
                        error=None,
                        attempt_count=attempt
                    )

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    # Rate limit hit
                    logger.warning(
                        f"Rate limit hit for PDL (attempt {attempt})"
                    )
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    logger.error(f"HTTP error from PDL: {e}")
                    circuit_breaker.record_failure()
                    break

            except (httpx.TimeoutException, httpx.RequestError) as e:
                logger.warning(
                    f"Network error with PDL (attempt {attempt}): {e}"
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                circuit_breaker.record_failure()

            except Exception as e:
                logger.error(f"Unexpected error with PDL: {e}")
                circuit_breaker.record_failure()
                break

        return IntelligenceResult(
            source=source,
            success=False,
            data=None,
            error="Failed after retries",
            attempt_count=self.max_retries
        )

    async def _fetch_apollo_people(
        self,
        company_name: str,
        domain: str
    ) -> IntelligenceResult:
        """
        Fetch executive/people data from Apollo.io.

        Args:
            company_name: Name of the company
            domain: Company domain

        Returns:
            IntelligenceResult with Apollo people data
        """
        source = DataSource.APOLLO
        circuit_breaker = self.circuit_breakers[source]

        if not circuit_breaker.can_execute():
            logger.warning(f"Circuit breaker open for {source.value} (people)")
            return IntelligenceResult(
                source=source,
                success=False,
                data=None,
                error="Circuit breaker open",
                attempt_count=0
            )

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    # Search for C-level executives at the company
                    response = await client.post(
                        "https://api.apollo.io/v1/mixed_people/search",
                        json={
                            "organization_domains": [domain],
                            "person_titles": ["CEO", "CTO", "CFO", "CIO", "CISO", "COO", "CPO", "President", "VP"],
                            "per_page": 10,
                            "page": 1
                        },
                        headers={
                            "Content-Type": "application/json",
                            "X-Api-Key": self.apollo_api_key
                        }
                    )

                    response.raise_for_status()
                    data = response.json()

                    circuit_breaker.record_success()

                    logger.info(
                        f"Successfully fetched Apollo people data for {company_name} "
                        f"({len(data.get('people', []))} executives found)"
                    )

                    return IntelligenceResult(
                        source=source,
                        success=True,
                        data={"type": "people", "people": data.get("people", [])},
                        error=None,
                        attempt_count=attempt
                    )

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    logger.warning(f"Rate limit hit for Apollo people (attempt {attempt})")
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    logger.error(f"HTTP error from Apollo people: {e}")
                    circuit_breaker.record_failure()
                    break

            except Exception as e:
                logger.error(f"Unexpected error with Apollo people: {e}")
                circuit_breaker.record_failure()
                break

        return IntelligenceResult(
            source=source,
            success=False,
            data=None,
            error="Failed after retries (people)",
            attempt_count=self.max_retries
        )

    async def _fetch_pdl_people(
        self,
        company_name: str,
        domain: str
    ) -> IntelligenceResult:
        """
        Fetch executive/people data from PeopleDataLabs.

        Args:
            company_name: Name of the company
            domain: Company domain

        Returns:
            IntelligenceResult with PDL people data
        """
        source = DataSource.PDL
        circuit_breaker = self.circuit_breakers[source]

        if not circuit_breaker.can_execute():
            logger.warning(f"Circuit breaker open for {source.value} (people)")
            return IntelligenceResult(
                source=source,
                success=False,
                data=None,
                error="Circuit breaker open",
                attempt_count=0
            )

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    # Search for C-level executives
                    response = await client.get(
                        "https://api.peopledatalabs.com/v5/person/search",
                        params={
                            "query": {
                                "job_company_website": domain,
                                "job_title_role": ["ceo", "cto", "cfo", "cio", "ciso", "coo", "cpo", "president", "vp"]
                            },
                            "size": 10,
                            "pretty": True
                        },
                        headers={
                            "X-Api-Key": self.pdl_api_key
                        }
                    )

                    response.raise_for_status()
                    data = response.json()

                    circuit_breaker.record_success()

                    logger.info(
                        f"Successfully fetched PDL people data for {company_name} "
                        f"({len(data.get('data', []))} executives found)"
                    )

                    return IntelligenceResult(
                        source=source,
                        success=True,
                        data={"type": "people", "people": data.get("data", [])},
                        error=None,
                        attempt_count=attempt
                    )

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    logger.warning(f"Rate limit hit for PDL people (attempt {attempt})")
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    logger.error(f"HTTP error from PDL people: {e}")
                    circuit_breaker.record_failure()
                    break

            except Exception as e:
                logger.error(f"Unexpected error with PDL people: {e}")
                circuit_breaker.record_failure()
                break

        return IntelligenceResult(
            source=source,
            success=False,
            data=None,
            error="Failed after retries (people)",
            attempt_count=self.max_retries
        )

    async def _fetch_zoominfo_data(
        self,
        company_name: str,
        domain: str
    ) -> IntelligenceResult:
        """
        Fetch company data from ZoomInfo with circuit breaker.

        Args:
            company_name: Name of the company
            domain: Company domain

        Returns:
            IntelligenceResult with ZoomInfo company data
        """
        source = DataSource.ZOOMINFO
        circuit_breaker = self.circuit_breakers[source]

        if not circuit_breaker.can_execute():
            logger.warning(f"Circuit breaker open for {source.value}")
            return IntelligenceResult(
                source=source, success=False, data=None,
                error="Circuit breaker open", attempt_count=0
            )

        try:
            result = await self.zoominfo_client.enrich_company(
                domain=domain, company_name=company_name
            )
            if result.get("success"):
                circuit_breaker.record_success()
                logger.info(f"Successfully fetched ZoomInfo data for {company_name}")
                return IntelligenceResult(
                    source=source, success=True,
                    data=result.get("normalized", result.get("data", {})),
                    error=None, attempt_count=1
                )
            else:
                circuit_breaker.record_failure()
                return IntelligenceResult(
                    source=source, success=False, data=None,
                    error=result.get("error", "Unknown error"), attempt_count=1
                )

        except Exception as e:
            logger.error(f"Unexpected error with ZoomInfo: {e}")
            circuit_breaker.record_failure()
            return IntelligenceResult(
                source=source, success=False, data=None,
                error=str(e), attempt_count=1
            )

    async def _fetch_zoominfo_people(
        self,
        company_name: str,
        domain: str
    ) -> IntelligenceResult:
        """
        Fetch executive/people data from ZoomInfo.

        Args:
            company_name: Name of the company
            domain: Company domain

        Returns:
            IntelligenceResult with ZoomInfo people data
        """
        source = DataSource.ZOOMINFO
        circuit_breaker = self.circuit_breakers[source]

        if not circuit_breaker.can_execute():
            logger.warning(f"Circuit breaker open for {source.value} (people)")
            return IntelligenceResult(
                source=source, success=False, data=None,
                error="Circuit breaker open", attempt_count=0
            )

        try:
            result = await self.zoominfo_client.search_contacts(
                domain=domain,
                job_titles=["CEO", "CTO", "CFO", "CIO", "CISO", "COO", "CPO",
                            "President", "VP"]
            )
            if result.get("success"):
                circuit_breaker.record_success()
                logger.info(
                    f"Successfully fetched ZoomInfo people data for {company_name} "
                    f"({len(result.get('people', []))} executives found)"
                )
                return IntelligenceResult(
                    source=source, success=True,
                    data={"type": "people", "people": result.get("people", [])},
                    error=None, attempt_count=1
                )
            else:
                circuit_breaker.record_failure()
                return IntelligenceResult(
                    source=source, success=False, data=None,
                    error=result.get("error", "Unknown error"), attempt_count=1
                )

        except Exception as e:
            logger.error(f"Unexpected error with ZoomInfo people: {e}")
            circuit_breaker.record_failure()
            return IntelligenceResult(
                source=source, success=False, data=None,
                error=str(e), attempt_count=1
            )
