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
    1. Run all 20 specialists in parallel
    2. Aggregate results with central LLM
    """
    logger.info(f"Starting LLM Council for {company_data.get('company_name')}")

    # Step 1: Run all specialists in parallel
    specialist_tasks = [
        run_specialist(specialist, company_data, apollo_data, pdl_data)
        for specialist in SPECIALISTS
    ]

    specialist_results = await asyncio.gather(*specialist_tasks, return_exceptions=True)

    # Filter out exceptions
    valid_results = []
    for i, result in enumerate(specialist_results):
        if isinstance(result, Exception):
            logger.error(f"Specialist {SPECIALISTS[i]['id']} failed: {result}")
        else:
            valid_results.append(result)

    logger.info(f"Completed {len(valid_results)}/{len(SPECIALISTS)} specialist analyses")

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

    # Add metadata
    final_result["_council_metadata"] = {
        "specialists_run": len(valid_results),
        "specialists_total": len(SPECIALISTS),
        "timestamp": datetime.utcnow().isoformat(),
        "specialist_results": valid_results
    }

    logger.info(f"LLM Council completed for {company_data.get('company_name')}")

    return final_result


async def validate_with_council(company_data: Dict, apollo_data: Dict, pdl_data: Dict) -> Dict[str, Any]:
    """
    Main entry point for LLM Council validation.
    Returns validated, concise, fact-driven company data.
    """
    try:
        result = await run_council(company_data, apollo_data, pdl_data)

        # Ensure we have minimum required fields
        if not result.get("company_name"):
            result["company_name"] = company_data.get("company_name", "Unknown")
        if not result.get("domain"):
            result["domain"] = company_data.get("domain", "Unknown")
        if not result.get("confidence_score"):
            result["confidence_score"] = 0.7

        return result

    except Exception as e:
        logger.error(f"LLM Council error: {e}")
        # Return basic data on failure
        return {
            "company_name": company_data.get("company_name", "Unknown"),
            "domain": company_data.get("domain", "Unknown"),
            "industry": company_data.get("industry", "Unknown"),
            "confidence_score": 0.3,
            "error": str(e)
        }
