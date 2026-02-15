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
        self.zoominfo_client_id = os.environ.get("ZOOMINFO_CLIENT_ID")
        self.zoominfo_client_secret = os.environ.get("ZOOMINFO_CLIENT_SECRET")

        # Validate environment variables
        self._validate_environment()

        # Initialize components
        self.intelligence_gatherer = IntelligenceGatherer(
            apollo_api_key=self.apollo_api_key,
            pdl_api_key=self.pdl_api_key,
            zoominfo_access_token=self.zoominfo_access_token,
            zoominfo_client_id=self.zoominfo_client_id,
            zoominfo_client_secret=self.zoominfo_client_secret
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
        if self.zoominfo_client_id and self.zoominfo_client_secret:
            try:
                self.zoominfo_client = ZoomInfoClient(
                    client_id=self.zoominfo_client_id,
                    client_secret=self.zoominfo_client_secret
                )
                logger.info("ZoomInfo client initialized (auto-auth)")
            except ValueError as e:
                logger.warning(f"ZoomInfo client initialization failed: {e}")
        elif self.zoominfo_access_token:
            try:
                self.zoominfo_client = ZoomInfoClient(
                    access_token=self.zoominfo_access_token
                )
                logger.info("ZoomInfo client initialized (static token)")
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
            if self.zoominfo_access_token or (self.zoominfo_client_id and self.zoominfo_client_secret):
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

            # Step 6.5: Determine strategic roles and filter to top 3 REAL contacts
            try:
                logger.info("Step 6.5: Determining strategic roles and filtering contacts")
                strategic_roles = await self.llm_council.determine_strategic_roles(
                    validated_data["data"],
                    pain_points=enriched_data.get("pain_points")
                )
                logger.info(f"Strategic roles identified: {strategic_roles}")

                # Get ENRICHED stakeholders (with strategic_priorities, conversation_starters)
                # Use enriched version if available, otherwise use original
                stakeholders_to_filter = enriched_data.get("stakeholder_profiles", stakeholder_profiles)

                # Filter enriched stakeholder_profiles to match strategic roles (REAL contacts only)
                strategic_contacts = self._match_strategic_contacts(
                    stakeholders_to_filter,
                    strategic_roles
                )

                # Update validated_data with filtered strategic contacts (with enrichment preserved)
                validated_data["data"]["stakeholder_profiles"] = strategic_contacts
                logger.info(f"Filtered to {len(strategic_contacts)} enriched strategic contacts matching target roles")

            except Exception as e:
                logger.warning(f"Strategic role filtering failed, using all contacts: {e}")

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

        # Generate intent topics (PRIORITIZE ZoomInfo buyer intent data)
        # Only generate with LLM if ZoomInfo intent signals are missing or insufficient
        if zoominfo_signals.get("intent_signals") and len(zoominfo_signals["intent_signals"]) >= 3:
            # Use ZoomInfo intent signals directly (PRIMARY data source)
            enriched["intent_topics"] = zoominfo_signals["intent_signals"]
            logger.info(f"Using {len(zoominfo_signals['intent_signals'])} ZoomInfo intent signals (PRIMARY)")
        else:
            # Fallback: Generate with LLM if ZoomInfo data is insufficient
            intent_topics = await self.llm_council.generate_intent_topics(
                company_data,
                enrichment_context
            )
            if intent_topics:
                enriched["intent_topics"] = intent_topics
                logger.info(f"Generated {len(intent_topics)} intent topics with LLM (ZoomInfo unavailable)")

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

        # Add ZoomInfo-specific enrichment data (PRIMARY source - always include)
        # These are PRIORITIZED over LLM-generated data
        if zoominfo_signals.get("technologies"):
            enriched["technology_stack"] = zoominfo_signals["technologies"]
            enriched["technologies"] = zoominfo_signals["technologies"]  # Alias for template
            logger.info(f"Included {len(zoominfo_signals['technologies'])} ZoomInfo technology installations")

        if zoominfo_signals.get("intent_signals"):
            enriched["buyer_intent_signals"] = zoominfo_signals["intent_signals"]
            # Also set as intent_topics if not already set by LLM
            if "intent_topics" not in enriched:
                enriched["intent_topics"] = zoominfo_signals["intent_signals"]
            logger.info(f"Included {len(zoominfo_signals['intent_signals'])} ZoomInfo intent signals")

        if zoominfo_signals.get("scoops"):
            enriched["business_scoops"] = zoominfo_signals["scoops"]
            enriched["scoops"] = zoominfo_signals["scoops"]  # Alias for template
            logger.info(f"Included {len(zoominfo_signals['scoops'])} ZoomInfo business scoops")

        logger.info(f"Enriched data with {len(enriched)} new fields")
        return enriched

    def _match_strategic_contacts(
        self,
        stakeholder_profiles: list,
        strategic_roles: list
    ) -> list:
        """
        Match real contacts to strategic roles identified by LLM Council.

        Prioritizes contacts whose roles match the strategic target roles.
        Returns up to 3 contacts matching strategic roles (REAL contacts only).

        Args:
            stakeholder_profiles: All available real contacts
            strategic_roles: 3 strategic roles to target (from LLM Council)

        Returns:
            Filtered list of up to 3 stakeholder profiles matching strategic roles
        """
        if not stakeholder_profiles:
            logger.warning("No stakeholder profiles available to match strategic roles")
            return []

        if not strategic_roles:
            logger.warning("No strategic roles provided, returning all profiles")
            return stakeholder_profiles[:3]

        matched_contacts = []
        used_roles = set()

        # For each strategic role, find the best matching real contact
        for target_role in strategic_roles:
            if len(matched_contacts) >= 3:
                break

            # Normalize target role for matching
            target_role_lower = target_role.lower().strip()
            target_role_words = target_role_lower.split()

            best_match = None
            best_score = 0

            for contact in stakeholder_profiles:
                # Skip if already matched
                if contact in matched_contacts:
                    continue

                title = contact.get('title', '').lower()

                # Calculate match score
                score = 0

                # Exact match
                if target_role_lower in title:
                    score = 100
                # Partial match (e.g., "CIO" in "Chief Information Officer")
                elif any(word in title for word in target_role_words if len(word) >= 3):
                    score = 80
                # Role acronym match (e.g., "cio" matches "chief information officer")
                elif target_role_lower == 'cio' and ('chief information' in title or 'information officer' in title):
                    score = 90
                elif target_role_lower == 'cto' and ('chief technology' in title or 'technology officer' in title):
                    score = 90
                elif target_role_lower == 'cfo' and ('chief financial' in title or 'financial officer' in title):
                    score = 90
                elif target_role_lower == 'ciso' and ('chief security' in title or 'security officer' in title or 'chief information security' in title):
                    score = 90
                elif target_role_lower == 'coo' and ('chief operating' in title or 'operating officer' in title):
                    score = 90
                elif target_role_lower == 'cpo' and ('chief product' in title or 'product officer' in title):
                    score = 90
                # VP matches
                elif 'vp' in target_role_lower and 'vp' in title:
                    # Check if department matches
                    if any(word in title for word in target_role_words if word not in ['vp', 'of']):
                        score = 70
                    else:
                        score = 50

                if score > best_score:
                    best_score = score
                    best_match = contact

            # Add best match if found and score is decent
            if best_match and best_score >= 50:
                matched_contacts.append(best_match)
                used_roles.add(target_role)
                logger.info(f"Matched {best_match.get('title')} to strategic role {target_role} (score: {best_score})")

        # If we don't have 3 matches, add highest-level remaining contacts
        if len(matched_contacts) < 3:
            logger.info(f"Only found {len(matched_contacts)} matching strategic roles, adding senior contacts")
            for contact in stakeholder_profiles:
                if contact not in matched_contacts:
                    matched_contacts.append(contact)
                    if len(matched_contacts) >= 3:
                        break

        logger.info(f"Final strategic contacts: {len(matched_contacts)}")
        return matched_contacts[:3]

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
                    # Initialize variables
                    name = ""
                    email = None
                    phone = None
                    linkedin = None
                    title = ""
                    direct_phone = None
                    mobile_phone = None
                    company_phone = None
                    first_name = ""
                    last_name = ""
                    department = ""
                    management_level = ""
                    person_id = ""

                    # Extract name and contact info based on source
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
                        # ZoomInfo contacts already normalized by ZoomInfoClient with full enrichment
                        name = person.get("name", "")
                        email = person.get("email")
                        # ZoomInfo provides multiple phone types - prioritize direct > mobile > general
                        phone = person.get("direct_phone") or person.get("mobile_phone") or person.get("phone")
                        linkedin = person.get("linkedin")
                        title = person.get("title", "")
                        # Store all ZoomInfo enriched fields
                        direct_phone = person.get("direct_phone")
                        mobile_phone = person.get("mobile_phone")
                        company_phone = person.get("company_phone")
                        first_name = person.get("first_name", "")
                        last_name = person.get("last_name", "")
                        department = person.get("department", "")
                        management_level = person.get("management_level", "")
                        person_id = person.get("person_id", "")
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

                    # Build stakeholder profile with all available data
                    profile = {
                        "name": name,
                        "title": title,
                        "email": email or "Not available",
                        "phone": phone or "Not available",
                        "linkedin": linkedin or "Not available",
                        "source": result.source.value
                    }

                    # Add ZoomInfo-specific enriched fields if available
                    if result.source.value == "zoominfo":
                        if direct_phone:
                            profile["direct_phone"] = direct_phone
                        if mobile_phone:
                            profile["mobile_phone"] = mobile_phone
                        if company_phone:
                            profile["company_phone"] = company_phone
                        if first_name:
                            profile["first_name"] = first_name
                        if last_name:
                            profile["last_name"] = last_name
                        if department:
                            profile["department"] = department
                        if management_level:
                            profile["management_level"] = management_level
                        if person_id:
                            profile["person_id"] = person_id

                    stakeholders.append(profile)

        # Count stakeholders with phone numbers
        with_phones = sum(1 for s in stakeholders if s.get("phone") and s["phone"] != "Not available")
        with_direct = sum(1 for s in stakeholders if s.get("direct_phone"))
        with_mobile = sum(1 for s in stakeholders if s.get("mobile_phone"))

        logger.info(f"✅ Processed {len(stakeholders)} stakeholder profiles")
        logger.info(f"   - {with_phones} with phone numbers")
        logger.info(f"   - {with_direct} with direct phone")
        logger.info(f"   - {with_mobile} with mobile phone")
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

        # Define source reliability - ZoomInfo is PRIMARY source (TIER_1)
        # Apollo and PDL are secondary sources (TIER_2)
        source_reliability = {
            "zoominfo": SourceTier.TIER_1,  # PRIMARY - Highest priority
            "apollo": SourceTier.TIER_2,    # Secondary fallback
            "peopledatalabs": SourceTier.TIER_2  # Secondary fallback
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

        # CRITICAL: Merge ALL comprehensive data from ALL sources
        # Priority: ZoomInfo (TIER_1) > Apollo (TIER_2) > PDL (TIER_2)
        data_dict = {
            "company_name": company_name,
            "domain": domain,
            **validated_fields  # Validated core fields
        }

        # Merge comprehensive ZoomInfo data (50+ fields) - HIGHEST PRIORITY
        if "zoominfo" in sources_data:
            zi_data = sources_data["zoominfo"]
            # Merge ALL ZoomInfo fields (don't overwrite validated core fields)
            for key, value in zi_data.items():
                if key not in data_dict and value:  # Only add if not already set
                    data_dict[key] = value

            # ZoomInfo-specific enrichment data (always include these)
            if "intent_signals" in zi_data:
                data_dict["intent_signals"] = zi_data["intent_signals"]
                logger.info(f"   ✓ Intent signals: {len(zi_data['intent_signals'])} signals")
            if "scoops" in zi_data:
                data_dict["scoops"] = zi_data["scoops"]
                logger.info(f"   ✓ Business scoops: {len(zi_data['scoops'])} events")
            if "news_articles" in zi_data:
                data_dict["news_articles"] = zi_data["news_articles"]
                logger.info(f"   ✓ News articles: {len(zi_data['news_articles'])} articles")
            if "technology_installs" in zi_data:
                data_dict["technology_installs"] = zi_data["technology_installs"]
                logger.info(f"   ✓ Technology installs: {len(zi_data['technology_installs'])} technologies")

            logger.info(f"Merged {len(zi_data)} ZoomInfo fields (PRIMARY source)")

        # Merge Apollo data for missing fields - SECONDARY PRIORITY
        if "apollo" in sources_data:
            apollo_data = sources_data["apollo"]
            fields_added = 0
            for key, value in apollo_data.items():
                if key not in data_dict and value:  # Fill gaps only
                    data_dict[key] = value
                    fields_added += 1
            if fields_added > 0:
                logger.info(f"Added {fields_added} missing fields from Apollo (secondary source)")

        # Merge PDL data for any remaining gaps - SECONDARY PRIORITY
        if "peopledatalabs" in sources_data:
            pdl_data = sources_data["peopledatalabs"]
            fields_added = 0
            for key, value in pdl_data.items():
                if key not in data_dict and value:  # Fill gaps only
                    data_dict[key] = value
                    fields_added += 1
            if fields_added > 0:
                logger.info(f"Added {fields_added} missing fields from PDL (secondary source)")

        # Add stakeholder profiles if provided
        if stakeholder_profiles:
            data_dict["stakeholder_profiles"] = stakeholder_profiles

        logger.info(f"Final merged data contains {len(data_dict)} total fields")

        return {
            "data": data_dict,
            "confidence_score": avg_confidence,
            "metadata": {
                "validated_fields": len(validated_fields),
                "total_fields": len(fields_to_validate),
                "merged_fields": len(data_dict),
                "stakeholders_count": len(stakeholder_profiles) if stakeholder_profiles else 0,
                "sources_used": list(sources_data.keys()),
                "primary_source": "zoominfo" if "zoominfo" in sources_data else (
                    "apollo" if "apollo" in sources_data else (
                        "peopledatalabs" if "peopledatalabs" in sources_data else "none"
                    )
                )
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
