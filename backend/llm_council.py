"""
LLM Council for Company Data Validation
20 Specialist LLMs + 1 Aggregator for fact-driven, concise output.
"""
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import os

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 20 Specialist LLM Personalities
SPECIALISTS = [
    {
        "id": "industry_classifier",
        "name": "Industry Classification Expert",
        "focus": "industry",
        "prompt": """You are an industry classification expert. Analyze the company data and determine:
- Primary industry (use standard NAICS/SIC categories)
- Sub-industry or vertical
- Industry keywords
Be specific. Output JSON: {"industry": "...", "sub_industry": "...", "industry_keywords": [...]}"""
    },
    {
        "id": "employee_analyst",
        "name": "Employee Count Analyst",
        "focus": "employee_count",
        "prompt": """You are an employee count analyst. Analyze the data and determine:
- Exact employee count if available, or best estimate
- Employee count range
- Growth trend if detectable
Be precise with numbers. Output JSON: {"employee_count": number_or_null, "employee_range": "...", "headcount_trend": "..."}"""
    },
    {
        "id": "revenue_analyst",
        "name": "Revenue & Financial Analyst",
        "focus": "revenue",
        "prompt": """You are a financial analyst. Analyze and determine:
- Annual revenue (exact or estimate)
- Revenue range
- Funding information if available
Use specific numbers, not ranges like "millions". Output JSON: {"annual_revenue": "...", "revenue_range": "...", "funding": "..."}"""
    },
    {
        "id": "geo_specialist",
        "name": "Geographic Presence Specialist",
        "focus": "geography",
        "prompt": """You are a geographic presence specialist. Determine:
- Headquarters location (city, state/province, country)
- List of countries with operations (list actual country names, max 20)
- Regional presence
Be specific - list actual locations, not "worldwide" or "global". Output JSON: {"headquarters": "City, State, Country", "countries": ["Country1", "Country2", ...], "regions": [...]}"""
    },
    {
        "id": "founding_historian",
        "name": "Company History Expert",
        "focus": "history",
        "prompt": """You are a company historian. Determine:
- Founding year
- Founders (names if available)
- Key milestones
Be factual. Output JSON: {"founded_year": number_or_null, "founders": [...], "milestones": [...]}"""
    },
    {
        "id": "tech_stack_expert",
        "name": "Technology Stack Expert",
        "focus": "technology",
        "prompt": """You are a technology analyst. Identify:
- Core technologies used
- Tech stack categories
- Technical capabilities
List specific technologies, not general terms. Output JSON: {"technologies": [...], "tech_categories": [...], "capabilities": [...]}"""
    },
    {
        "id": "market_analyst",
        "name": "Target Market Analyst",
        "focus": "target_market",
        "prompt": """You are a market analyst. Determine:
- Primary target market (B2B, B2C, B2G, etc.)
- Target customer segments (be specific)
- Market verticals served
Be specific about who they sell to. Output JSON: {"market_type": "...", "customer_segments": [...], "verticals": [...]}"""
    },
    {
        "id": "product_analyst",
        "name": "Product & Services Analyst",
        "focus": "products",
        "prompt": """You are a product analyst. Identify:
- Main products or services (list them)
- Product categories
- Key offerings
List actual product names if available. Output JSON: {"products": [...], "services": [...], "categories": [...]}"""
    },
    {
        "id": "competitor_analyst",
        "name": "Competitive Intelligence Analyst",
        "focus": "competitors",
        "prompt": """You are a competitive intelligence analyst. Identify:
- Direct competitors (company names)
- Competitive advantages
- Market position
List actual competitor names. Output JSON: {"competitors": [...], "advantages": [...], "market_position": "..."}"""
    },
    {
        "id": "leadership_analyst",
        "name": "Leadership & Executive Analyst",
        "focus": "leadership",
        "prompt": """You are an executive analyst. Identify:
- CEO name
- Key executives (names and titles)
- Leadership team size
Use actual names. Output JSON: {"ceo": "...", "executives": [{"name": "...", "title": "..."}], "leadership_size": number}"""
    },
    {
        "id": "social_analyst",
        "name": "Social Media & Web Presence Analyst",
        "focus": "social",
        "prompt": """You are a digital presence analyst. Identify:
- LinkedIn URL
- Twitter/X handle
- Other social profiles
- Website domain
Provide actual URLs/handles. Output JSON: {"linkedin": "...", "twitter": "...", "website": "...", "other_social": [...]}"""
    },
    {
        "id": "legal_analyst",
        "name": "Legal & Corporate Structure Analyst",
        "focus": "legal",
        "prompt": """You are a corporate structure analyst. Identify:
- Company type (public, private, subsidiary, etc.)
- Stock ticker if public
- Parent company if subsidiary
Be specific. Output JSON: {"company_type": "...", "ticker": "...", "parent_company": "..."}"""
    },
    {
        "id": "growth_analyst",
        "name": "Growth & Trajectory Analyst",
        "focus": "growth",
        "prompt": """You are a growth analyst. Assess:
- Growth stage (startup, growth, mature, etc.)
- Recent growth indicators
- Expansion signals
Output JSON: {"growth_stage": "...", "growth_indicators": [...], "expansion_signals": [...]}"""
    },
    {
        "id": "brand_analyst",
        "name": "Brand & Reputation Analyst",
        "focus": "brand",
        "prompt": """You are a brand analyst. Assess:
- Brand recognition level
- Key brand attributes
- Notable awards or recognition
Output JSON: {"brand_level": "...", "brand_attributes": [...], "awards": [...]}"""
    },
    {
        "id": "partnership_analyst",
        "name": "Partnerships & Alliances Analyst",
        "focus": "partnerships",
        "prompt": """You are a partnerships analyst. Identify:
- Key partners (company names)
- Partnership types
- Integration ecosystem
List actual partner names. Output JSON: {"partners": [...], "partnership_types": [...], "ecosystem": [...]}"""
    },
    {
        "id": "customer_analyst",
        "name": "Customer Base Analyst",
        "focus": "customers",
        "prompt": """You are a customer analyst. Identify:
- Notable customers (company names if B2B)
- Customer count estimate
- Customer segments
List actual customer names if available. Output JSON: {"notable_customers": [...], "customer_count": "...", "segments": [...]}"""
    },
    {
        "id": "pricing_analyst",
        "name": "Pricing & Business Model Analyst",
        "focus": "pricing",
        "prompt": """You are a pricing analyst. Identify:
- Business model type
- Pricing model (subscription, one-time, freemium, etc.)
- Price points if available
Output JSON: {"business_model": "...", "pricing_model": "...", "price_points": [...]}"""
    },
    {
        "id": "culture_analyst",
        "name": "Company Culture Analyst",
        "focus": "culture",
        "prompt": """You are a culture analyst. Identify:
- Company values
- Work culture indicators
- Employee benefits highlights
Output JSON: {"values": [...], "culture_type": "...", "benefits": [...]}"""
    },
    {
        "id": "innovation_analyst",
        "name": "Innovation & R&D Analyst",
        "focus": "innovation",
        "prompt": """You are an innovation analyst. Identify:
- R&D focus areas
- Patents or IP (count if available)
- Innovation initiatives
Output JSON: {"rd_focus": [...], "patent_count": number_or_null, "innovations": [...]}"""
    },
    {
        "id": "risk_analyst",
        "name": "Risk & Compliance Analyst",
        "focus": "risk",
        "prompt": """You are a risk analyst. Identify:
- Compliance certifications (ISO, SOC2, etc.)
- Regulatory considerations
- Risk factors
List specific certifications. Output JSON: {"certifications": [...], "regulations": [...], "risk_factors": [...]}"""
    },
]

# Aggregator prompt
AGGREGATOR_PROMPT = """You are the Chief Data Aggregator. You have received analyses from 20 specialist LLMs about a company.

Your job is to:
1. Synthesize all specialist inputs into a single, authoritative company profile
2. Resolve any conflicts by choosing the most specific/accurate data
3. BE CONCISE AND FACT-DRIVEN - no verbose language
4. List specifics instead of generalizations (e.g., list actual country names, not "operates globally")
5. Use actual numbers, not ranges when possible
6. Remove any fluff or marketing language

CRITICAL OUTPUT RULES:
- geographic_reach: List actual country names (max 20), NOT "190 countries worldwide"
- employee_count: Use a number or specific range, NOT "large workforce"
- revenue: Use specific figures, NOT "significant revenue"
- target_market: List specific segments, NOT "various industries"
- technologies: List actual tech names, NOT "modern technology stack"

Output a clean JSON object with these fields:
{
    "company_name": "...",
    "domain": "...",
    "industry": "...",
    "sub_industry": "...",
    "employee_count": number or "X-Y",
    "annual_revenue": "specific figure or estimate",
    "headquarters": "City, State, Country",
    "geographic_reach": ["Country1", "Country2", ...],
    "founded_year": number,
    "founders": ["Name1", "Name2"],
    "ceo": "Name",
    "target_market": "B2B/B2C/B2G",
    "customer_segments": ["Segment1", "Segment2"],
    "products": ["Product1", "Product2"],
    "technologies": ["Tech1", "Tech2"],
    "competitors": ["Competitor1", "Competitor2"],
    "company_type": "Public/Private/Subsidiary",
    "linkedin_url": "...",
    "confidence_score": 0.0-1.0
}

SPECIALIST INPUTS:
{specialist_inputs}

ORIGINAL DATA SOURCES:
Apollo.io: {apollo_data}
PeopleDataLabs: {pdl_data}

Output ONLY valid JSON, no explanation."""


async def call_openai(prompt: str, system_prompt: str, model: str = "gpt-4o-mini") -> Dict[str, Any]:
    """Call OpenAI API with given prompts."""
    if not OPENAI_API_KEY:
        logger.warning("OpenAI API key not configured")
        return {}

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return {}
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return {}


async def run_specialist(specialist: Dict, company_data: Dict, apollo_data: Dict, pdl_data: Dict) -> Dict[str, Any]:
    """Run a single specialist LLM."""
    data_context = f"""
Company: {company_data.get('company_name', 'Unknown')}
Domain: {company_data.get('domain', 'Unknown')}

Apollo.io Data: {json.dumps(apollo_data, indent=2) if apollo_data else 'No data'}

PeopleDataLabs Data: {json.dumps(pdl_data, indent=2) if pdl_data else 'No data'}

Analyze this data for your specialty: {specialist['focus']}
"""

    result = await call_openai(data_context, specialist['prompt'])

    return {
        "specialist_id": specialist['id'],
        "specialist_name": specialist['name'],
        "focus": specialist['focus'],
        "analysis": result,
        "timestamp": datetime.utcnow().isoformat()
    }


async def run_council(company_data: Dict, apollo_data: Dict, pdl_data: Dict) -> Dict[str, Any]:
    """
    Run the full LLM Council:
    1. Run specialists in batches of 5 to avoid rate limits
    2. Aggregate results with central LLM
    """
    logger.info(f"Starting LLM Council for {company_data.get('company_name')}")

    # Step 1: Run specialists in batches of 5 to avoid rate limits
    valid_results = []
    batch_size = 5

    for i in range(0, len(SPECIALISTS), batch_size):
        batch = SPECIALISTS[i:i + batch_size]
        logger.info(f"Running specialist batch {i//batch_size + 1}/{(len(SPECIALISTS) + batch_size - 1)//batch_size}")

        batch_tasks = [
            run_specialist(specialist, company_data, apollo_data, pdl_data)
            for specialist in batch
        ]

        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

        for j, result in enumerate(batch_results):
            if isinstance(result, Exception):
                logger.error(f"Specialist {batch[j]['id']} failed: {result}")
            elif result.get("analysis"):  # Only add if we got actual analysis
                valid_results.append(result)

        # Small delay between batches to avoid rate limits
        if i + batch_size < len(SPECIALISTS):
            await asyncio.sleep(0.5)

    logger.info(f"Completed {len(valid_results)}/{len(SPECIALISTS)} specialist analyses")

    # If no specialists returned data, return empty result with metadata
    if len(valid_results) == 0:
        logger.warning("No specialists returned data, skipping aggregator")
        return {
            "_council_metadata": {
                "specialists_run": 0,
                "specialists_total": len(SPECIALISTS),
                "timestamp": datetime.utcnow().isoformat(),
                "specialist_results": [],
                "mode": "no_specialist_data"
            }
        }

    # Step 2: Run aggregator
    specialist_inputs_text = "\n\n".join([
        f"=== {r['specialist_name']} ({r['focus']}) ===\n{json.dumps(r['analysis'], indent=2)}"
        for r in valid_results
    ])

    aggregator_prompt = AGGREGATOR_PROMPT.format(
        specialist_inputs=specialist_inputs_text,
        apollo_data=json.dumps(apollo_data, indent=2) if apollo_data else "No data",
        pdl_data=json.dumps(pdl_data, indent=2) if pdl_data else "No data"
    )

    logger.info("Running aggregator LLM...")
    final_result = await call_openai(
        aggregator_prompt,
        "You are a data aggregator. Output only valid JSON.",
        model="gpt-4o-mini"
    )

    # If aggregator failed, return empty with metadata
    if not final_result:
        logger.warning("Aggregator returned no data")
        final_result = {}

    # Add metadata
    final_result["_council_metadata"] = {
        "specialists_run": len(valid_results),
        "specialists_total": len(SPECIALISTS),
        "timestamp": datetime.utcnow().isoformat(),
        "specialist_results": valid_results
    }

    logger.info(f"LLM Council completed for {company_data.get('company_name')}")

    return final_result


def title_case_name(name: str) -> str:
    """Properly capitalize a name (handles McName, O'Name, etc.)."""
    if not name:
        return name
    # Handle already uppercase acronyms
    if name.isupper() and len(name) <= 4:
        return name
    # Title case with special handling
    words = name.split()
    result = []
    for word in words:
        if word.lower() in ['ceo', 'cfo', 'cto', 'coo', 'vp', 'svp', 'evp']:
            result.append(word.upper())
        elif "'" in word:  # O'Brien, etc.
            parts = word.split("'")
            result.append("'".join(p.capitalize() for p in parts))
        elif word.lower().startswith('mc'):  # McDonald, etc.
            result.append('Mc' + word[2:].capitalize())
        else:
            result.append(word.capitalize())
    return ' '.join(result)


def extract_base_data(company_data: Dict, apollo_data: Dict, pdl_data: Dict) -> Dict[str, Any]:
    """Extract data directly from API responses as fallback."""
    result = {
        "company_name": title_case_name(company_data.get("company_name", "Unknown")),
        "domain": company_data.get("domain", "Unknown"),
        "industry": company_data.get("industry", "Unknown"),
        "confidence_score": 0.6
    }

    # Extract from Apollo data
    apollo_org = None
    if apollo_data:
        if "organization" in apollo_data:
            apollo_org = apollo_data.get("organization", {})
        elif "organizations" in apollo_data:
            orgs = apollo_data.get("organizations", [])
            if orgs:
                apollo_org = orgs[0]
        elif "accounts" in apollo_data:
            accounts = apollo_data.get("accounts", [])
            if accounts:
                apollo_org = accounts[0]

    if apollo_org:
        if apollo_org.get("name"):
            result["company_name"] = title_case_name(apollo_org["name"])
        if apollo_org.get("industry"):
            result["industry"] = title_case_name(apollo_org["industry"])
        if apollo_org.get("estimated_num_employees"):
            result["employee_count"] = apollo_org["estimated_num_employees"]
        if apollo_org.get("annual_revenue"):
            result["annual_revenue"] = apollo_org["annual_revenue"]
        elif apollo_org.get("annual_revenue_printed"):
            result["annual_revenue"] = apollo_org["annual_revenue_printed"]
        if apollo_org.get("city") and apollo_org.get("country"):
            city = title_case_name(apollo_org['city'])
            state = title_case_name(apollo_org.get('state', ''))
            country = title_case_name(apollo_org['country'])
            result["headquarters"] = f"{city}, {state}, {country}".replace(", ,", ",").strip(", ")
        if apollo_org.get("founded_year"):
            result["founded_year"] = apollo_org["founded_year"]
        if apollo_org.get("linkedin_url"):
            result["linkedin_url"] = apollo_org["linkedin_url"]
        if apollo_org.get("keywords"):
            result["technologies"] = apollo_org["keywords"][:10]
        # CEO from Apollo (if available in organization data)
        if apollo_org.get("ceo") or apollo_org.get("ceo_name"):
            result["ceo"] = title_case_name(apollo_org.get("ceo") or apollo_org.get("ceo_name"))

    # Extract from PDL data - PDL returns data directly at top level
    pdl_company = pdl_data if pdl_data and pdl_data.get("name") else None

    if pdl_company:
        if pdl_company.get("name"):
            result["company_name"] = title_case_name(pdl_company["name"])
        if pdl_company.get("industry"):
            result["industry"] = title_case_name(pdl_company["industry"])
        if pdl_company.get("employee_count"):
            result["employee_count"] = pdl_company["employee_count"]
        elif pdl_company.get("size"):
            result["employee_count"] = pdl_company["size"]
        # Revenue from PDL
        if pdl_company.get("inferred_revenue"):
            result["annual_revenue"] = pdl_company["inferred_revenue"]
        elif pdl_company.get("estimated_annual_revenue"):
            result["annual_revenue"] = pdl_company["estimated_annual_revenue"]
        if pdl_company.get("location"):
            loc = pdl_company["location"]
            if isinstance(loc, dict):
                locality = title_case_name(loc.get('locality', ''))
                region = title_case_name(loc.get('region', ''))
                country = title_case_name(loc.get('country', ''))
                result["headquarters"] = f"{locality}, {region}, {country}".strip(", ").replace(", ,", ",")
            elif isinstance(loc, str):
                result["headquarters"] = loc
        if pdl_company.get("founded"):
            result["founded_year"] = pdl_company["founded"]
        if pdl_company.get("linkedin_url"):
            result["linkedin_url"] = pdl_company["linkedin_url"]
        if pdl_company.get("tags"):
            result["technologies"] = pdl_company["tags"][:10]
        if pdl_company.get("type"):
            result["target_market"] = pdl_company["type"]
        if pdl_company.get("location") and isinstance(pdl_company["location"], dict):
            result["geographic_reach"] = [pdl_company["location"].get("country", "Unknown")]

    return result


async def validate_with_council(company_data: Dict, apollo_data: Dict, pdl_data: Dict) -> Dict[str, Any]:
    """
    Main entry point for LLM Council validation.
    Returns validated, concise, fact-driven company data.
    Falls back to direct extraction if council fails.
    """
    # Always extract base data first as fallback
    base_data = extract_base_data(company_data, apollo_data, pdl_data)

    if not OPENAI_API_KEY:
        logger.warning("OpenAI not configured, using direct extraction")
        base_data["_council_metadata"] = {"specialists_run": 0, "specialists_total": 20, "mode": "direct_extraction"}
        return base_data

    try:
        result = await run_council(company_data, apollo_data, pdl_data)

        # Check if council returned useful data (more than just metadata)
        useful_fields = [k for k in result.keys() if not k.startswith("_") and result[k]]
        if len(useful_fields) < 3:
            logger.warning(f"Council returned minimal data ({len(useful_fields)} fields), using fallback")
            # Merge council result with base data, preferring council values
            merged = {**base_data, **{k: v for k, v in result.items() if v}}
            merged["confidence_score"] = 0.65
            return merged

        # Ensure we have minimum required fields by merging with base data
        for key, value in base_data.items():
            if key not in result or not result.get(key):
                result[key] = value

        if not result.get("confidence_score"):
            result["confidence_score"] = 0.8

        return result

    except Exception as e:
        logger.error(f"LLM Council error: {e}")
        # Return base data on failure
        base_data["confidence_score"] = 0.5
        base_data["_council_metadata"] = {"error": str(e), "specialists_run": 0, "mode": "fallback"}
        return base_data
