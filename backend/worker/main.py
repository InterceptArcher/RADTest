"""
Main worker orchestrator for ephemeral Railway workers.
Coordinates intelligence gathering, validation, and storage.
"""
import asyncio
import logging
import sys
from typing import Dict, Any
import os

from intelligence_gatherer import IntelligenceGatherer, DataSource
from supabase_injector import SupabaseInjector
from llm_validator import LLMValidator
from llm_council import LLMCouncil, SourceTier
from gamma_slideshow import GammaSlideshowCreator
from hunter_client import HunterClient
from zoominfo_client import ZoomInfoClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


class WorkerOrchestrator:
    """
    Orchestrates the complete data extraction and processing pipeline.

    Pipeline:
    1. Intelligence gathering from Apollo.io and PeopleDataLabs
    2. Raw data injection into Supabase
    3. Data validation using LLM agents/council
    4. Finalized data storage
    5. Slideshow generation
    """

    def __init__(self):
        """
        Initialize worker with all required components.

        All API keys and credentials must be provided via environment variables.
        """
        # Load environment variables
        self.apollo_api_key = os.environ.get("APOLLO_API_KEY")
        self.pdl_api_key = os.environ.get("PDL_API_KEY")
        self.supabase_url = os.environ.get("SUPABASE_URL")
        self.supabase_key = os.environ.get("SUPABASE_KEY")
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.gamma_api_key = os.environ.get("GAMMA_API_KEY")
        self.zoominfo_access_token = os.environ.get("ZOOMINFO_ACCESS_TOKEN")

        # Validate environment variables
        self._validate_environment()

        # Initialize components
        self.intelligence_gatherer = IntelligenceGatherer(
            apollo_api_key=self.apollo_api_key,
            pdl_api_key=self.pdl_api_key,
            zoominfo_access_token=self.zoominfo_access_token
        )

        self.supabase_injector = SupabaseInjector(
            supabase_url=self.supabase_url,
            supabase_key=self.supabase_key
        )

        self.llm_validator = LLMValidator(
            openai_api_key=self.openai_api_key
        )

        self.llm_council = LLMCouncil(
            openai_api_key=self.openai_api_key,
            council_size=12
        )

        self.gamma_creator = GammaSlideshowCreator(
            gamma_api_key=self.gamma_api_key
        )

        self.hunter_client = HunterClient(
            api_key=os.environ.get("HUNTER_API_KEY")
        )

        # Initialize ZoomInfo client (optional - for intent/scoops/tech data)
        self.zoominfo_client = None
        if self.zoominfo_access_token:
            try:
                self.zoominfo_client = ZoomInfoClient(
                    access_token=self.zoominfo_access_token
                )
                logger.info("ZoomInfo client initialized")
            except ValueError as e:
                logger.warning(f"ZoomInfo client initialization failed: {e}")

        logger.info("Worker orchestrator initialized successfully")

    def _validate_environment(self):
        """
        Validate that all required environment variables are set.

        Raises:
            ValueError: If any required variable is missing
        """
        required_vars = [
            "APOLLO_API_KEY",
            "PDL_API_KEY",
            "SUPABASE_URL",
            "SUPABASE_KEY",
            "OPENAI_API_KEY",
            "GAMMA_API_KEY"
        ]

        missing = [var for var in required_vars if not os.environ.get(var)]

        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}. "
                "These values must be provided via environment variables."
            )

    async def process_company_request(
        self,
        company_name: str,
        domain: str,
        requested_by: str
    ) -> Dict[str, Any]:
        """
        Process a complete company profile request.

        Args:
            company_name: Name of the company
            domain: Company domain
            requested_by: User who requested the profile

        Returns:
            Dictionary with processing results and slideshow URL

        Raises:
            Exception: If processing fails
        """
        logger.info(
            f"Starting profile processing for {company_name} ({domain})"
        )

        try:
            # Step 1: Gather intelligence from external sources
            logger.info("Step 1: Gathering intelligence")
            sources = [DataSource.APOLLO, DataSource.PDL]
            if self.zoominfo_access_token:
                sources.append(DataSource.ZOOMINFO)
            intelligence_results = await self.intelligence_gatherer.gather_company_intelligence(
                company_name=company_name,
                domain=domain,
                sources=sources
            )

            # Step 2: Inject raw data into Supabase
            logger.info("Step 2: Injecting raw data")
            raw_records = []
            for result in intelligence_results:
                if result.success and result.data:
                    raw_records.append({
                        "company_name": company_name,
                        "domain": domain,
                        "source": result.source.value,
                        "raw_data": result.data
                    })

            if raw_records:
                await self.supabase_injector.inject_batch_raw_data(raw_records)

            # Step 3: Extract and process people data
            logger.info("Step 3: Processing executive/stakeholder data")
            stakeholder_profiles = self._process_people_data(intelligence_results)

            # Step 3.5: Enrich emails with Hunter.io
            if stakeholder_profiles:
                try:
                    logger.info("Step 3.5: Verifying and enriching emails")
                    stakeholder_profiles = await self.hunter_client.enrich_stakeholder_emails(
                        stakeholder_profiles,
                        domain
                    )
                except Exception as e:
                    logger.warning(f"Email enrichment failed, continuing with basic emails: {e}")

            # Step 4: Fetch and process news data
            news_data = {}
            try:
                logger.info("Step 4: Fetching news and signals")
                from news_gatherer import NewsGatherer
                news_gatherer = NewsGatherer()
                news_data = await news_gatherer.fetch_company_news(company_name, domain)
            except Exception as e:
                logger.warning(f"News gathering failed, continuing without news: {e}")
                news_data = {"success": False}

            # Step 4.5: Fetch ZoomInfo intent signals, scoops, and tech data
            zoominfo_signals = {}
            if self.zoominfo_client:
                try:
                    logger.info("Step 4.5: Fetching ZoomInfo intent signals and scoops")
                    intent_result, scoops_result, tech_result = await asyncio.gather(
                        self.zoominfo_client.enrich_intent(domain),
                        self.zoominfo_client.search_scoops(domain),
                        self.zoominfo_client.enrich_technologies(domain),
                        return_exceptions=True
                    )
                    if isinstance(intent_result, dict) and intent_result.get("success"):
                        zoominfo_signals["intent_signals"] = intent_result["intent_signals"]
                    if isinstance(scoops_result, dict) and scoops_result.get("success"):
                        zoominfo_signals["scoops"] = scoops_result["scoops"]
                    if isinstance(tech_result, dict) and tech_result.get("success"):
                        zoominfo_signals["technologies"] = tech_result["technologies"]
                    logger.info(f"ZoomInfo signals collected: {list(zoominfo_signals.keys())}")
                except Exception as e:
                    logger.warning(f"ZoomInfo signals fetch failed, continuing: {e}")

            # Step 5: Data validation and normalization
            logger.info("Step 5: Validating and normalizing data")
            validated_data = await self._validate_and_normalize(
                company_name,
                domain,
                intelligence_results,
                stakeholder_profiles
            )

            # Step 6: Enrich data with LLM-generated insights
            try:
                logger.info("Step 6: Generating pain points, opportunities, and intent signals")
                enriched_data = await self._enrich_with_llm(
                    validated_data["data"],
                    news_data,
                    stakeholder_profiles,
                    zoominfo_signals=zoominfo_signals
                )
                # Merge enriched data
                validated_data["data"].update(enriched_data)
            except Exception as e:
                logger.warning(f"LLM enrichment failed, continuing with basic data: {e}")
                # Continue without enrichment

            # Step 7: Inject finalized data
            logger.info("Step 7: Injecting finalized data")
            finalize_result = await self.supabase_injector.inject_finalized_data(
                company_name=company_name,
                domain=domain,
                validated_data=validated_data["data"],
                confidence_score=validated_data["confidence_score"],
                validation_metadata=validated_data["metadata"]
            )

            # Step 8: Generate slideshow
            logger.info("Step 8: Generating slideshow")
            slideshow_data = {
                "company_name": company_name,
                "validated_data": validated_data["data"],
                "confidence_score": validated_data["confidence_score"],
                "validation_metadata": validated_data["metadata"]
            }

            slideshow_result = await self.gamma_creator.create_slideshow(
                company_data=slideshow_data,
                user_email=requested_by
            )

            logger.info(
                f"Profile processing complete for {company_name}. "
                f"Slideshow: {slideshow_result.get('slideshow_url')}"
            )

            return {
                "success": True,
                "company_name": company_name,
                "domain": domain,
                "slideshow_url": slideshow_result.get("slideshow_url"),
                "confidence_score": validated_data["confidence_score"],
                "finalize_record_id": finalize_result["record_id"],
                "requested_by": requested_by
            }

        except Exception as e:
            logger.error(f"Failed to process company request: {e}", exc_info=True)
            raise

    async def _enrich_with_llm(
        self,
        company_data: Dict[str, Any],
        news_data: Dict[str, Any],
        stakeholder_profiles: list,
        zoominfo_signals: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Enrich company data with LLM-generated insights.

        Args:
            company_data: Validated company data
            news_data: News articles and summaries
            stakeholder_profiles: List of stakeholder profiles
            zoominfo_signals: Optional ZoomInfo intent/scoops/tech data

        Returns:
            Dictionary with enriched data fields
        """
        enriched = {}
        zoominfo_signals = zoominfo_signals or {}

        # Merge ZoomInfo intent signals into news data for richer context
        enrichment_context = dict(news_data) if news_data else {}
        if zoominfo_signals.get("intent_signals"):
            enrichment_context["zoominfo_intent"] = zoominfo_signals["intent_signals"]
        if zoominfo_signals.get("scoops"):
            enrichment_context["zoominfo_scoops"] = zoominfo_signals["scoops"]

        # Generate pain points (enhanced with ZoomInfo intent/scoops)
        pain_points = await self.llm_council.generate_pain_points(
            company_data,
            enrichment_context
        )
        if pain_points:
            enriched["pain_points"] = pain_points

        # Generate opportunities based on pain points
        opportunities = await self.llm_council.generate_opportunities(
            company_data,
            pain_points
        )
        if opportunities:
            enriched["sales_opportunities"] = opportunities

        # Generate intent topics (enhanced with ZoomInfo buyer intent)
        intent_topics = await self.llm_council.generate_intent_topics(
            company_data,
            enrichment_context
        )
        if intent_topics:
            enriched["intent_topics"] = intent_topics

        # Enrich stakeholder profiles
        if stakeholder_profiles:
            enriched_stakeholders = await self.llm_council.enrich_stakeholder_profiles(
                stakeholder_profiles,
                company_data
            )
            enriched["stakeholder_profiles"] = enriched_stakeholders

        # Add news summaries
        if news_data.get("success"):
            enriched["news_triggers"] = news_data.get("summaries", {})

        # Add ZoomInfo-specific enrichment data
        if zoominfo_signals.get("technologies"):
            enriched["technology_stack"] = zoominfo_signals["technologies"]
        if zoominfo_signals.get("intent_signals"):
            enriched["buyer_intent_signals"] = zoominfo_signals["intent_signals"]
        if zoominfo_signals.get("scoops"):
            enriched["business_scoops"] = zoominfo_signals["scoops"]

        logger.info(f"Enriched data with {len(enriched)} new fields")
        return enriched

    def _process_people_data(self, intelligence_results: list) -> list:
        """
        Process and merge people/executive data from multiple sources.

        Args:
            intelligence_results: List of IntelligenceResult objects

        Returns:
            List of stakeholder profile dictionaries
        """
        stakeholders = []
        seen_names = set()

        for result in intelligence_results:
            if not result.success or not result.data:
                continue

            # Check if this is people data
            if result.data.get("type") == "people":
                people_list = result.data.get("people", [])

                for person in people_list:
                    # Extract name
                    if result.source.value == "apollo":
                        first_name = person.get("first_name", "")
                        last_name = person.get("last_name", "")
                        name = f"{first_name} {last_name}".strip()
                        email = person.get("email")
                        phone = person.get("phone_numbers", [{}])[0].get("raw_number") if person.get("phone_numbers") else None
                        linkedin = person.get("linkedin_url")
                        title = person.get("title", "")
                    elif result.source.value == "peopledatalabs":
                        name = person.get("full_name", "")
                        email = person.get("work_email") or person.get("personal_emails", [None])[0]
                        phone = person.get("phone_numbers", [None])[0]
                        linkedin = person.get("linkedin_url")
                        title = person.get("job_title", "")
                    elif result.source.value == "zoominfo":
                        # ZoomInfo contacts already normalized by ZoomInfoClient
                        name = person.get("name", "")
                        email = person.get("email")
                        phone = person.get("phone")
                        linkedin = person.get("linkedin")
                        title = person.get("title", "")
                    else:
                        continue

                    # Skip if no name
                    if not name:
                        continue

                    # Deduplicate by name
                    name_lower = name.lower()
                    if name_lower in seen_names:
                        continue

                    seen_names.add(name_lower)

                    stakeholders.append({
                        "name": name,
                        "title": title,
                        "email": email or "Not available",
                        "phone": phone or "Not available",
                        "linkedin": linkedin or "Not available",
                        "source": result.source.value
                    })

        logger.info(f"Processed {len(stakeholders)} stakeholder profiles")
        return stakeholders

    async def _validate_and_normalize(
        self,
        company_name: str,
        domain: str,
        intelligence_results: list,
        stakeholder_profiles: list = None
    ) -> Dict[str, Any]:
        """
        Validate and normalize data from multiple sources.

        Args:
            company_name: Name of the company
            domain: Company domain
            intelligence_results: List of IntelligenceResult objects

        Returns:
            Dictionary with validated data, confidence score, and metadata
        """
        # Extract data from successful results
        sources_data = {}
        for result in intelligence_results:
            if result.success and result.data:
                sources_data[result.source.value] = result.data

        if not sources_data:
            raise ValueError("No successful intelligence data to validate")

        # Define source reliability
        source_reliability = {
            "apollo": SourceTier.TIER_1,
            "peopledatalabs": SourceTier.TIER_1,
            "zoominfo": SourceTier.TIER_1
        }

        # Fields to validate
        fields_to_validate = [
            "employee_count",
            "revenue",
            "headquarters",
            "industry",
            "founded_year",
            "ceo"
        ]

        validated_fields = {}
        total_confidence = 0.0

        # Validate each field
        for field_name in fields_to_validate:
            # Extract candidate values from all sources
            candidates = []

            for source_name, source_data in sources_data.items():
                if field_name in source_data:
                    candidates.append({
                        "value": source_data[field_name],
                        "source": source_name,
                        "timestamp": source_data.get("last_updated", ""),
                        "metadata": {}
                    })

            if not candidates:
                continue

            # Use LLM council for conflicting data
            if len(candidates) > 1:
                decision = await self.llm_council.resolve_conflict(
                    field_name=field_name,
                    field_type="text",
                    candidate_values=candidates,
                    source_reliability=source_reliability
                )

                validated_fields[field_name] = decision.winner_value
                total_confidence += decision.confidence_score

            else:
                # Single source, no conflict
                validated_fields[field_name] = candidates[0]["value"]
                total_confidence += 1.0

        # Calculate average confidence
        avg_confidence = total_confidence / len(fields_to_validate) if fields_to_validate else 0.0

        # Add stakeholder profiles if provided
        data_dict = {
            "company_name": company_name,
            "domain": domain,
            **validated_fields
        }

        if stakeholder_profiles:
            data_dict["stakeholder_profiles"] = stakeholder_profiles

        return {
            "data": data_dict,
            "confidence_score": avg_confidence,
            "metadata": {
                "validated_fields": len(validated_fields),
                "total_fields": len(fields_to_validate),
                "stakeholders_count": len(stakeholder_profiles) if stakeholder_profiles else 0,
                "sources_used": list(sources_data.keys())
            }
        }


async def main():
    """
    Main entry point for the worker.

    Expects environment variable COMPANY_DATA with JSON containing:
    - company_name
    - domain
    - requested_by
    """
    import json

    # Load company data from environment
    company_data_str = os.environ.get("COMPANY_DATA")

    if not company_data_str:
        logger.error("COMPANY_DATA environment variable not set")
        sys.exit(1)

    try:
        company_data = json.loads(company_data_str)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid COMPANY_DATA JSON: {e}")
        sys.exit(1)

    # Validate required fields
    required_fields = ["company_name", "domain", "requested_by"]
    missing = [f for f in required_fields if f not in company_data]

    if missing:
        logger.error(f"Missing required fields in COMPANY_DATA: {missing}")
        sys.exit(1)

    # Initialize orchestrator and process
    orchestrator = WorkerOrchestrator()

    try:
        result = await orchestrator.process_company_request(
            company_name=company_data["company_name"],
            domain=company_data["domain"],
            requested_by=company_data["requested_by"]
        )

        logger.info("Worker completed successfully")
        logger.info(f"Result: {json.dumps(result, indent=2)}")

        # Write result to output file for Railway
        with open("/output/result.json", "w") as f:
            json.dump(result, f, indent=2)

    except Exception as e:
        logger.error(f"Worker failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
