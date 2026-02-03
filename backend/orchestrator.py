"""
Orchestrator LLM for Intelligent API Routing.

This module provides intelligent API selection for company data queries.
Instead of blindly querying all APIs, the orchestrator analyzes required
data points and assigns the most capable APIs for each.

Rule: Minimum 2 APIs per data point for data validation and completeness.
"""
import os
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# Data points required for final output, mapped to capable APIs
DATA_POINTS = {
    "executive_snapshot": {
        "account_name": ["apollo", "pdl", "hunter"],
        "company_overview": ["apollo", "pdl", "gnews"],
        "account_type": ["pdl", "apollo"],
        "industry": ["apollo", "pdl", "hunter"],
        "estimated_it_budget": ["pdl", "apollo"],
        "installed_technologies": ["pdl", "apollo"]
    },
    "buying_signals": {
        "intent_topics": ["gnews", "pdl", "apollo"],
        "interest_over_time": ["gnews", "pdl"],
        "partner_mentions": ["gnews", "apollo"],
        "key_signals": ["gnews", "apollo", "pdl"]
    },
    "opportunity_themes": {
        "pain_points": ["gnews", "pdl", "apollo"],
        "sales_opportunities": ["gnews", "apollo", "pdl"],
        "solution_areas": ["pdl", "apollo", "gnews"]
    },
    "stakeholder_map": {
        "executives": ["apollo", "hunter"],
        "bios": ["apollo", "hunter", "pdl"],
        "strategic_priorities": ["gnews", "apollo"],
        "communication_preferences": ["apollo", "hunter"],
        "conversation_starters": ["gnews", "apollo"],
        "next_steps": ["gnews", "apollo", "pdl"]
    },
    "supporting_assets": {
        "email_templates": ["hunter", "apollo"],
        "linkedin_outreach": ["apollo", "pdl"],
        "call_scripts": ["apollo", "pdl", "gnews"]
    }
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
        "description": "Apollo.io excels at contact discovery, executive information, and organizational data. Best choice for stakeholder mapping and contact details."
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
        "description": "PeopleDataLabs provides excellent technographic data, IT budget estimates, and technology stack information. Best for understanding installed technologies and company classification."
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
        "description": "Hunter.io specializes in email discovery and verification. Use when you need verified email addresses and contact information."
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
        "description": "GNews API provides recent company news for identifying buying signals, trigger events, and market intelligence. Essential for opportunity themes and timing insights."
    }
}


@dataclass
class OrchestratorResult:
    """Result from orchestrator analysis."""
    apis_to_query: List[str]
    data_point_api_mapping: Dict[str, List[str]]
    reasoning: str
    priority_order: List[str]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    orchestrator_version: str = "1.0"


def get_default_query_plan() -> OrchestratorResult:
    """
    Get default query plan that queries all APIs.
    Used as fallback when orchestrator fails or is disabled.
    """
    all_apis = list(API_CAPABILITIES.keys())

    # Build comprehensive mapping
    mapping = {}
    for category, points in DATA_POINTS.items():
        for point_name, apis in points.items():
            mapping[f"{category}.{point_name}"] = apis[:2]  # Take first 2 for each

    return OrchestratorResult(
        apis_to_query=all_apis,
        data_point_api_mapping=mapping,
        reasoning="Default plan: querying all APIs for comprehensive data coverage.",
        priority_order=["apollo", "pdl", "hunter", "gnews"]
    )


def build_orchestrator_prompt(company_data: Dict[str, Any]) -> str:
    """Build the prompt for the orchestrator LLM."""
    company_name = company_data.get("company_name", "Unknown")
    domain = company_data.get("domain", "unknown.com")
    industry = company_data.get("industry", "")

    return f"""You are an intelligent API orchestrator for a sales intelligence platform.

COMPANY TO ANALYZE:
- Name: {company_name}
- Domain: {domain}
- Industry hint: {industry or "Not specified"}

AVAILABLE APIs AND THEIR STRENGTHS:

1. APOLLO.IO:
   Best for: {', '.join(API_CAPABILITIES['apollo']['best_for'])}
   Provides: {', '.join(API_CAPABILITIES['apollo']['provides'])}

2. PEOPLEDATALABS (PDL):
   Best for: {', '.join(API_CAPABILITIES['pdl']['best_for'])}
   Provides: {', '.join(API_CAPABILITIES['pdl']['provides'])}

3. HUNTER.IO:
   Best for: {', '.join(API_CAPABILITIES['hunter']['best_for'])}
   Provides: {', '.join(API_CAPABILITIES['hunter']['provides'])}

4. GNEWS:
   Best for: {', '.join(API_CAPABILITIES['gnews']['best_for'])}
   Provides: {', '.join(API_CAPABILITIES['gnews']['provides'])}

REQUIRED OUTPUT DATA POINTS:

1. EXECUTIVE SNAPSHOT:
   - Account name, Company overview, Account type (public/private)
   - Industry, Estimated IT Budget, Installed technologies

2. BUYING SIGNALS:
   - Top 3 Intent Topics, Interest over time, Partner mentions, Key signals from news

3. OPPORTUNITY THEMES:
   - Pain points (3), Sales opportunities (3), Recommended solution areas (3)

4. STAKEHOLDER MAP (for CIO/CTO/CISO/COO/CFO/CPO):
   - Bio, Strategic priorities, Communication preferences, Conversation starters, Next steps

5. SUPPORTING ASSETS:
   - Email templates, LinkedIn outreach, Call scripts per contact

RULES:
1. Assign MINIMUM 2 APIs to each data point category for validation
2. Prioritize APIs based on their strengths for each data point
3. Consider the company context when making decisions
4. Always include GNews for buying signals and opportunity themes
5. Always include Apollo or Hunter for stakeholder data

OUTPUT FORMAT (JSON only, no explanation):
{{
    "apis_to_query": ["api1", "api2", ...],
    "priority_order": ["most_important_api", "second", ...],
    "data_point_mapping": {{
        "executive_snapshot": ["api1", "api2"],
        "buying_signals": ["api1", "api2"],
        "opportunity_themes": ["api1", "api2"],
        "stakeholder_map": ["api1", "api2"],
        "supporting_assets": ["api1", "api2"]
    }},
    "reasoning": "Brief explanation of API selection strategy"
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
                            "content": "You are an API orchestrator. Output only valid JSON, no explanation."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500
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

    Args:
        company_data: Dictionary with company_name, domain, and optional industry

    Returns:
        OrchestratorResult with API assignments and reasoning
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
        data_point_mapping = llm_result.get("data_point_mapping", {})
        reasoning = llm_result.get("reasoning", "LLM-based selection")

        # Ensure all APIs are valid
        valid_apis = set(API_CAPABILITIES.keys())
        apis_to_query = [api for api in apis_to_query if api in valid_apis]

        # Ensure minimum coverage - at least apollo and gnews for core data
        if "apollo" not in apis_to_query:
            apis_to_query.append("apollo")
        if "gnews" not in apis_to_query:
            apis_to_query.append("gnews")

        # Ensure each category has at least 2 APIs
        for category in DATA_POINTS.keys():
            if category not in data_point_mapping:
                data_point_mapping[category] = DATA_POINTS[category].get(
                    list(DATA_POINTS[category].keys())[0], ["apollo", "pdl"]
                )[:2]
            elif len(data_point_mapping[category]) < 2:
                # Add fallback APIs
                fallback = [api for api in valid_apis if api not in data_point_mapping[category]]
                data_point_mapping[category].extend(fallback[:2 - len(data_point_mapping[category])])

        return OrchestratorResult(
            apis_to_query=apis_to_query,
            data_point_api_mapping=data_point_mapping,
            reasoning=reasoning,
            priority_order=priority_order if priority_order else apis_to_query
        )

    except Exception as e:
        logger.error(f"Error parsing orchestrator result: {e}")
        return get_default_query_plan()


def should_query_api(api_name: str, query_plan: OrchestratorResult) -> bool:
    """Check if a specific API should be queried based on the plan."""
    return api_name in query_plan.apis_to_query


def get_api_priority(api_name: str, query_plan: OrchestratorResult) -> int:
    """Get the priority order for an API (lower = higher priority)."""
    try:
        return query_plan.priority_order.index(api_name)
    except ValueError:
        return len(query_plan.priority_order)  # Put at end if not found
