"""
Orchestrator LLM for Intelligent API Routing at BULLET-POINT Level.

This module provides intelligent API selection for company data queries.
Instead of blindly querying all APIs, the orchestrator analyzes required
data points and assigns the most capable APIs for EACH INDIVIDUAL FIELD.

Rule: Minimum 2 APIs per data point for data validation and completeness.
Rule: Hunter.io is ALWAYS queried for contact/stakeholder data.
"""
import os
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# GRANULAR DATA POINTS - Each individual bullet point mapped to capable APIs
# Format: "section.field" -> [list of APIs that can provide this data]
GRANULAR_DATA_POINTS = {
    # === EXECUTIVE SNAPSHOT ===
    "executive_snapshot.account_name": ["apollo", "pdl", "hunter", "zoominfo"],
    "executive_snapshot.company_overview": ["apollo", "pdl", "gnews", "zoominfo"],
    "executive_snapshot.account_type": ["pdl", "apollo"],
    "executive_snapshot.company_classification": ["pdl", "apollo"],
    "executive_snapshot.industry": ["apollo", "pdl", "hunter", "zoominfo"],
    "executive_snapshot.sub_industry": ["apollo", "pdl", "zoominfo"],
    "executive_snapshot.estimated_it_spend": ["pdl", "apollo", "zoominfo"],
    "executive_snapshot.employee_count": ["apollo", "pdl", "hunter", "zoominfo"],
    "executive_snapshot.annual_revenue": ["apollo", "pdl", "zoominfo"],
    "executive_snapshot.headquarters": ["apollo", "pdl", "hunter", "zoominfo"],
    "executive_snapshot.founded_year": ["apollo", "pdl", "zoominfo"],
    "executive_snapshot.installed_technologies": ["pdl", "apollo", "zoominfo"],

    # === BUYING SIGNALS ===
    "buying_signals.intent_topic_1": ["gnews", "pdl", "apollo", "zoominfo"],
    "buying_signals.intent_topic_2": ["gnews", "pdl", "apollo", "zoominfo"],
    "buying_signals.intent_topic_3": ["gnews", "pdl", "apollo", "zoominfo"],
    "buying_signals.intent_topic_1_description": ["gnews", "pdl", "zoominfo"],
    "buying_signals.intent_topic_2_description": ["gnews", "pdl", "zoominfo"],
    "buying_signals.intent_topic_3_description": ["gnews", "pdl", "zoominfo"],
    "buying_signals.interest_over_time": ["gnews", "pdl", "zoominfo"],
    "buying_signals.partner_mention_1": ["gnews", "apollo"],
    "buying_signals.partner_mention_2": ["gnews", "apollo"],
    "buying_signals.partner_mention_3": ["gnews", "apollo"],
    "buying_signals.key_signal_1": ["gnews", "apollo", "pdl", "zoominfo"],
    "buying_signals.key_signal_2": ["gnews", "apollo", "pdl", "zoominfo"],
    "buying_signals.key_signal_3": ["gnews", "apollo", "pdl", "zoominfo"],
    "buying_signals.signal_strength": ["gnews", "apollo", "pdl", "zoominfo"],
    "buying_signals.scoop_executive_hire": ["gnews", "apollo", "hunter", "zoominfo"],
    "buying_signals.scoop_funding": ["gnews", "apollo", "pdl", "zoominfo"],
    "buying_signals.scoop_expansion": ["gnews", "apollo", "zoominfo"],
    "buying_signals.scoop_ma": ["gnews", "apollo", "pdl", "zoominfo"],
    "buying_signals.scoop_product_launch": ["gnews", "apollo", "zoominfo"],

    # === OPPORTUNITY THEMES ===
    "opportunity_themes.pain_point_1": ["gnews", "pdl", "apollo", "zoominfo"],
    "opportunity_themes.pain_point_2": ["gnews", "pdl", "apollo", "zoominfo"],
    "opportunity_themes.pain_point_3": ["gnews", "pdl", "apollo", "zoominfo"],
    "opportunity_themes.sales_opportunity_1": ["gnews", "apollo", "pdl", "zoominfo"],
    "opportunity_themes.sales_opportunity_2": ["gnews", "apollo", "pdl", "zoominfo"],
    "opportunity_themes.sales_opportunity_3": ["gnews", "apollo", "pdl", "zoominfo"],
    "opportunity_themes.solution_area_1": ["pdl", "apollo", "gnews", "zoominfo"],
    "opportunity_themes.solution_area_2": ["pdl", "apollo", "gnews", "zoominfo"],
    "opportunity_themes.solution_area_3": ["pdl", "apollo", "gnews", "zoominfo"],

    # === STAKEHOLDER MAP (ZoomInfo PRIMARY, Hunter.io REQUIRED for email) ===
    "stakeholder_map.cio_name": ["zoominfo", "apollo", "hunter"],
    "stakeholder_map.cio_email": ["zoominfo", "hunter", "apollo"],
    "stakeholder_map.cio_bio": ["zoominfo", "apollo", "hunter", "pdl"],
    "stakeholder_map.cio_priorities": ["gnews", "apollo", "zoominfo"],
    "stakeholder_map.cto_name": ["zoominfo", "apollo", "hunter"],
    "stakeholder_map.cto_email": ["zoominfo", "hunter", "apollo"],
    "stakeholder_map.cto_bio": ["zoominfo", "apollo", "hunter", "pdl"],
    "stakeholder_map.cto_priorities": ["gnews", "apollo", "zoominfo"],
    "stakeholder_map.ciso_name": ["zoominfo", "apollo", "hunter"],
    "stakeholder_map.ciso_email": ["zoominfo", "hunter", "apollo"],
    "stakeholder_map.ciso_bio": ["zoominfo", "apollo", "hunter", "pdl"],
    "stakeholder_map.ciso_priorities": ["gnews", "apollo", "zoominfo"],
    "stakeholder_map.cfo_name": ["zoominfo", "apollo", "hunter"],
    "stakeholder_map.cfo_email": ["zoominfo", "hunter", "apollo"],
    "stakeholder_map.cfo_bio": ["zoominfo", "apollo", "hunter", "pdl"],
    "stakeholder_map.cfo_priorities": ["gnews", "apollo", "zoominfo"],
    "stakeholder_map.coo_name": ["zoominfo", "apollo", "hunter"],
    "stakeholder_map.coo_email": ["zoominfo", "hunter", "apollo"],
    "stakeholder_map.coo_bio": ["zoominfo", "apollo", "hunter", "pdl"],
    "stakeholder_map.coo_priorities": ["gnews", "apollo", "zoominfo"],
    "stakeholder_map.cpo_name": ["zoominfo", "apollo", "hunter"],
    "stakeholder_map.cpo_email": ["zoominfo", "hunter", "apollo"],
    "stakeholder_map.cpo_bio": ["zoominfo", "apollo", "hunter", "pdl"],
    "stakeholder_map.cpo_priorities": ["gnews", "apollo", "zoominfo"],
    "stakeholder_map.conversation_starters": ["gnews", "apollo", "zoominfo"],
    "stakeholder_map.recommended_next_steps": ["gnews", "apollo", "pdl", "zoominfo"],

    # === GROWTH METRICS (ZoomInfo exclusive/primary) ===
    "executive_snapshot.one_year_employee_growth": ["zoominfo"],
    "executive_snapshot.two_year_employee_growth": ["zoominfo"],
    "executive_snapshot.funding_amount": ["zoominfo", "pdl", "apollo"],
    "executive_snapshot.fortune_rank": ["zoominfo"],
    "executive_snapshot.num_locations": ["zoominfo", "pdl"],
    "executive_snapshot.business_model": ["zoominfo", "pdl"],

    # === PHONE NUMBERS (ZoomInfo Contact Enrich) ===
    "stakeholder_map.cio_direct_phone": ["zoominfo"],
    "stakeholder_map.cio_mobile_phone": ["zoominfo"],
    "stakeholder_map.cio_accuracy_score": ["zoominfo"],
    "stakeholder_map.cto_direct_phone": ["zoominfo"],
    "stakeholder_map.cto_mobile_phone": ["zoominfo"],
    "stakeholder_map.cto_accuracy_score": ["zoominfo"],
    "stakeholder_map.ciso_direct_phone": ["zoominfo"],
    "stakeholder_map.ciso_mobile_phone": ["zoominfo"],
    "stakeholder_map.ciso_accuracy_score": ["zoominfo"],
    "stakeholder_map.cfo_direct_phone": ["zoominfo"],
    "stakeholder_map.cfo_mobile_phone": ["zoominfo"],
    "stakeholder_map.cfo_accuracy_score": ["zoominfo"],
    "stakeholder_map.coo_direct_phone": ["zoominfo"],
    "stakeholder_map.coo_mobile_phone": ["zoominfo"],
    "stakeholder_map.coo_accuracy_score": ["zoominfo"],
    "stakeholder_map.cpo_direct_phone": ["zoominfo"],
    "stakeholder_map.cpo_mobile_phone": ["zoominfo"],
    "stakeholder_map.cpo_accuracy_score": ["zoominfo"],

    # === SUPPORTING ASSETS ===
    "supporting_assets.email_templates": ["hunter", "apollo"],
    "supporting_assets.linkedin_outreach": ["apollo", "pdl"],
    "supporting_assets.call_scripts": ["apollo", "pdl", "gnews"],

    # === NEWS INTELLIGENCE (minimum 2 APIs per field) ===
    "news_intelligence.executive_changes": ["gnews", "apollo"],
    "news_intelligence.funding": ["gnews", "apollo"],
    "news_intelligence.partnerships": ["gnews", "apollo"],
    "news_intelligence.expansions": ["gnews", "apollo"],
    "news_intelligence.key_insights": ["gnews", "apollo", "pdl"],
    "news_intelligence.sales_implications": ["gnews", "apollo"],
}


# API capabilities - what each API is best at
API_CAPABILITIES = {
    "apollo": {
        "best_for": [
            "contacts",
            "c-suite executives",
            "org data",
            "leadership",
            "company firmographics",
            "email addresses",
            "phone numbers",
            "linkedin profiles"
        ],
        "provides": [
            "company_name",
            "employee_count",
            "industry",
            "headquarters",
            "founded_year",
            "linkedin_url",
            "executives",
            "email",
            "phone",
            "annual_revenue"
        ],
        "description": "Apollo.io excels at contact discovery, executive information, and organizational data. Best choice for stakeholder mapping and contact details.",
        "required_for": ["stakeholder_map", "executive_snapshot"]
    },
    "pdl": {
        "best_for": [
            "technographics",
            "company enrichment",
            "employee data",
            "IT spend estimation",
            "technology stack",
            "company classification"
        ],
        "provides": [
            "technologies",
            "employee_count",
            "industry",
            "revenue",
            "type",
            "funding_details",
            "location",
            "tech_stack"
        ],
        "description": "PeopleDataLabs provides excellent technographic data, IT budget estimates, and technology stack information. Best for understanding installed technologies and company classification.",
        "required_for": ["executive_snapshot", "buying_signals"]
    },
    "hunter": {
        "best_for": [
            "email discovery",
            "domain verification",
            "contact details",
            "email patterns",
            "department contacts"
        ],
        "provides": [
            "emails",
            "contacts",
            "domain_verification",
            "organization",
            "email_patterns"
        ],
        "description": "Hunter.io specializes in email discovery and verification. REQUIRED for verified email addresses and stakeholder contact information.",
        "required_for": ["stakeholder_map", "supporting_assets"]  # ALWAYS required
    },
    "gnews": {
        "best_for": [
            "recent news",
            "buying signals",
            "market events",
            "executive changes",
            "funding announcements",
            "partnership news",
            "expansion signals",
            "product launches"
        ],
        "provides": [
            "executive_changes",
            "funding",
            "partnerships",
            "expansions",
            "products",
            "financial_news",
            "market_signals"
        ],
        "description": "GNews API provides recent company news for identifying buying signals, trigger events, and market intelligence. Essential for opportunity themes and timing insights.",
        "required_for": ["buying_signals", "opportunity_themes", "news_intelligence"]
    },
    "zoominfo": {
        "best_for": [
            "company enrichment",
            "contact discovery",
            "contact enrichment",
            "buyer intent signals",
            "business scoops",
            "technology stack",
            "executive data",
            "firmographic data",
            "phone numbers",
            "growth metrics",
            "corporate hierarchy"
        ],
        "provides": [
            "company_name",
            "employee_count",
            "revenue",
            "industry",
            "headquarters",
            "founded_year",
            "executives",
            "email",
            "phone",
            "direct_phone",
            "mobile_phone",
            "company_phone",
            "contact_accuracy_score",
            "linkedin",
            "intent_signals",
            "scoops",
            "technologies",
            "employee_growth",
            "funding_amount",
            "fortune_rank",
            "num_locations",
            "business_model"
        ],
        "description": "ZoomInfo GTM API provides premium company enrichment, executive contacts with direct/mobile phones, buyer intent signals, business scoops (hires, funding, expansion), installed technology data, and growth metrics. Acts as PRIMARY source and tiebreaker in LLM council when other sources disagree.",
        "required_for": ["executive_snapshot", "buying_signals", "stakeholder_map"]
    }
}


@dataclass
class OrchestratorResult:
    """Result from orchestrator analysis with GRANULAR field-level mapping."""
    apis_to_query: List[str]
    data_point_api_mapping: Dict[str, List[str]]  # Now contains EVERY field
    reasoning: str
    priority_order: List[str]
    granular_assignments: Dict[str, Dict[str, List[str]]]  # Section -> Field -> APIs
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    orchestrator_version: str = "2.0-granular"


def get_default_query_plan() -> OrchestratorResult:
    """
    Get default query plan that queries ALL APIs.
    Used as fallback when orchestrator fails or is disabled.
    Hunter.io is ALWAYS included for contact data.
    """
    # Always query all APIs - Hunter is critical for contacts
    all_apis = ["apollo", "pdl", "hunter", "gnews", "zoominfo"]

    # Build granular assignments from GRANULAR_DATA_POINTS
    granular_assignments = {}
    flat_mapping = {}

    for full_key, apis in GRANULAR_DATA_POINTS.items():
        section, field_name = full_key.split(".", 1)
        if section not in granular_assignments:
            granular_assignments[section] = {}
        granular_assignments[section][field_name] = apis[:2]  # Take first 2 for validation
        flat_mapping[full_key] = apis[:2]

    return OrchestratorResult(
        apis_to_query=all_apis,
        data_point_api_mapping=flat_mapping,
        reasoning="Default plan: querying ALL APIs for comprehensive data coverage. Hunter.io included for contact verification. ZoomInfo included for intent signals and scoops.",
        priority_order=["apollo", "hunter", "pdl", "zoominfo", "gnews"],  # Hunter prioritized
        granular_assignments=granular_assignments
    )


def build_orchestrator_prompt(company_data: Dict[str, Any]) -> str:
    """Build the prompt for the orchestrator LLM with GRANULAR field assignments."""
    company_name = company_data.get("company_name", "Unknown")
    domain = company_data.get("domain", "unknown.com")
    industry = company_data.get("industry", "")

    # Build detailed field list
    field_list = "\n".join([f"   - {k}: Best APIs = {', '.join(v)}" for k, v in list(GRANULAR_DATA_POINTS.items())[:30]])

    return f"""You are an intelligent API orchestrator for a sales intelligence platform.
You must assign APIs to EACH INDIVIDUAL DATA FIELD (bullet point), not just categories.

COMPANY TO ANALYZE:
- Name: {company_name}
- Domain: {domain}
- Industry hint: {industry or "Not specified"}

AVAILABLE APIs AND THEIR STRENGTHS:

1. APOLLO.IO:
   Best for: {', '.join(API_CAPABILITIES['apollo']['best_for'])}
   REQUIRED for: stakeholder_map, executive_snapshot

2. PEOPLEDATALABS (PDL):
   Best for: {', '.join(API_CAPABILITIES['pdl']['best_for'])}
   REQUIRED for: executive_snapshot, buying_signals

3. HUNTER.IO:
   Best for: {', '.join(API_CAPABILITIES['hunter']['best_for'])}
   REQUIRED for: stakeholder_map (emails), supporting_assets
   *** HUNTER MUST ALWAYS BE QUERIED FOR CONTACT DATA ***

4. GNEWS:
   Best for: {', '.join(API_CAPABILITIES['gnews']['best_for'])}
   REQUIRED for: buying_signals, opportunity_themes, news_intelligence

5. ZOOMINFO:
   Best for: {', '.join(API_CAPABILITIES['zoominfo']['best_for'])}
   REQUIRED for: executive_snapshot, buying_signals, stakeholder_map
   *** ZOOMINFO PROVIDES PREMIUM INTENT SIGNALS AND BUSINESS SCOOPS ***

EXAMPLE GRANULAR FIELD ASSIGNMENTS:
{field_list}
... and many more fields

CRITICAL RULES:
1. Assign MINIMUM 2 APIs to EACH field for validation
2. Hunter.io MUST be included for all stakeholder email/contact fields
3. GNews MUST be included for all news/signal/scoop fields
4. Every field in the output must have API assignments

OUTPUT FORMAT (JSON only, no explanation):
{{
    "apis_to_query": ["apollo", "hunter", "pdl", "gnews", "zoominfo"],
    "priority_order": ["apollo", "hunter", "pdl", "zoominfo", "gnews"],
    "granular_assignments": {{
        "executive_snapshot": {{
            "account_name": ["apollo", "pdl"],
            "company_overview": ["apollo", "pdl", "gnews"],
            "industry": ["apollo", "pdl"],
            "estimated_it_spend": ["pdl", "apollo"],
            "installed_technologies": ["pdl", "apollo"]
        }},
        "buying_signals": {{
            "intent_topic_1": ["gnews", "pdl"],
            "intent_topic_2": ["gnews", "pdl"],
            "intent_topic_3": ["gnews", "pdl"],
            "key_signal_1": ["gnews", "apollo"],
            "key_signal_2": ["gnews", "apollo"],
            "key_signal_3": ["gnews", "apollo"],
            "signal_strength": ["gnews", "apollo", "pdl"]
        }},
        "opportunity_themes": {{
            "pain_point_1": ["gnews", "pdl"],
            "pain_point_2": ["gnews", "pdl"],
            "pain_point_3": ["gnews", "pdl"],
            "sales_opportunity_1": ["gnews", "apollo"],
            "sales_opportunity_2": ["gnews", "apollo"],
            "sales_opportunity_3": ["gnews", "apollo"]
        }},
        "stakeholder_map": {{
            "cio_name": ["apollo", "hunter"],
            "cio_email": ["hunter", "apollo"],
            "cto_name": ["apollo", "hunter"],
            "cto_email": ["hunter", "apollo"]
        }},
        "news_intelligence": {{
            "executive_changes": ["gnews"],
            "funding": ["gnews", "apollo"],
            "partnerships": ["gnews"]
        }}
    }},
    "reasoning": "Brief explanation of API selection for each section"
}}"""


async def call_orchestrator_llm(prompt: str) -> Optional[Dict[str, Any]]:
    """Call OpenAI to get orchestrator decision."""
    if not OPENAI_API_KEY:
        logger.warning("OpenAI API key not configured, using default plan")
        return None

    try:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an API orchestrator. Output only valid JSON with granular field-level API assignments. ALWAYS include hunter in apis_to_query."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0,  # Set to 0 for deterministic API selection
                    "max_tokens": 1500  # Increased for granular output
                },
                timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]

                # Parse JSON from response
                # Handle potential markdown code blocks
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                return json.loads(content.strip())
            else:
                logger.error(f"OpenAI API error: {response.status_code}")
                return None

    except Exception as e:
        logger.error(f"Orchestrator LLM error: {e}")
        return None


async def analyze_and_plan(company_data: Dict[str, Any]) -> OrchestratorResult:
    """
    Analyze required data points and create an intelligent API query plan.
    Now with GRANULAR field-level assignments.

    Args:
        company_data: Dictionary with company_name, domain, and optional industry

    Returns:
        OrchestratorResult with API assignments for EACH field
    """
    # Handle empty/invalid input
    if not company_data or not company_data.get("company_name"):
        logger.warning("Empty company data, using default plan")
        return get_default_query_plan()

    # Build prompt and call LLM
    prompt = build_orchestrator_prompt(company_data)
    llm_result = await call_orchestrator_llm(prompt)

    if not llm_result:
        logger.info("Using default query plan (LLM unavailable)")
        return get_default_query_plan()

    try:
        # Validate and extract results
        apis_to_query = llm_result.get("apis_to_query", [])
        priority_order = llm_result.get("priority_order", apis_to_query)
        granular_assignments = llm_result.get("granular_assignments", {})
        reasoning = llm_result.get("reasoning", "LLM-based granular selection")

        # Ensure all APIs are valid
        valid_apis = set(API_CAPABILITIES.keys())
        apis_to_query = [api for api in apis_to_query if api in valid_apis]

        # CRITICAL: Hunter.io is ALWAYS required for contact data
        if "hunter" not in apis_to_query:
            apis_to_query.append("hunter")
            logger.info("Added Hunter.io to query plan (required for contacts)")

        # Ensure apollo is included for org data
        if "apollo" not in apis_to_query:
            apis_to_query.append("apollo")

        # Ensure gnews is included for news/signals
        if "gnews" not in apis_to_query:
            apis_to_query.append("gnews")

        # Ensure pdl is included for technographics
        if "pdl" not in apis_to_query:
            apis_to_query.append("pdl")

        # Ensure zoominfo is included for intent/scoops
        if "zoominfo" not in apis_to_query:
            apis_to_query.append("zoominfo")

        # Build flat mapping from granular assignments
        flat_mapping = {}
        for section, fields in granular_assignments.items():
            for field_name, apis in fields.items():
                flat_mapping[f"{section}.{field_name}"] = apis

        # Fill in any missing fields from default
        for full_key, default_apis in GRANULAR_DATA_POINTS.items():
            if full_key not in flat_mapping:
                flat_mapping[full_key] = default_apis[:2]
                section, field_name = full_key.split(".", 1)
                if section not in granular_assignments:
                    granular_assignments[section] = {}
                granular_assignments[section][field_name] = default_apis[:2]

        return OrchestratorResult(
            apis_to_query=apis_to_query,
            data_point_api_mapping=flat_mapping,
            reasoning=reasoning,
            priority_order=priority_order if priority_order else apis_to_query,
            granular_assignments=granular_assignments
        )

    except Exception as e:
        logger.error(f"Error parsing orchestrator result: {e}")
        return get_default_query_plan()


def should_query_api(api_name: str, query_plan: OrchestratorResult) -> bool:
    """
    Check if a specific API should be queried based on the plan.
    Hunter.io is ALWAYS queried regardless of plan (required for contacts).
    """
    # Hunter is ALWAYS required for contact/email data
    if api_name == "hunter":
        return True
    return api_name in query_plan.apis_to_query


def get_api_priority(api_name: str, query_plan: OrchestratorResult) -> int:
    """Get the priority order for an API (lower = higher priority)."""
    try:
        return query_plan.priority_order.index(api_name)
    except ValueError:
        return len(query_plan.priority_order)  # Put at end if not found


def get_apis_for_field(field_path: str, query_plan: OrchestratorResult) -> List[str]:
    """
    Get the list of APIs assigned to a specific field.

    Args:
        field_path: Full path like "executive_snapshot.company_overview"
        query_plan: The orchestrator result

    Returns:
        List of API names assigned to this field
    """
    return query_plan.data_point_api_mapping.get(
        field_path,
        GRANULAR_DATA_POINTS.get(field_path, ["apollo", "pdl"])
    )
