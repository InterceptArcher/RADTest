"""
LLM Council for Company Data Validation
20 Specialist LLMs + 1 Aggregator for fact-driven, concise output.
"""
import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
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
    # === NEW SPECIALISTS FOR EXPANDED INTELLIGENCE (21-28) ===
    {
        "id": "company_overview_writer",
        "name": "Company Overview Writer",
        "focus": "executive_snapshot",
        "prompt": """You are a company overview specialist. Write a concise executive-friendly overview:
- 2-3 sentence company description (who they are, what they do, key differentiators)
- Company classification (Public, Private, Government Contractor)
- Estimated annual IT spend based on: employee count, revenue, industry (tech=5-10% of revenue, others=3-5%)
Be factual and professional. Output JSON: {
    "company_overview": "2-3 sentence overview...",
    "company_classification": "Public/Private/Government",
    "estimated_it_spend": "$X-$Y million",
    "it_spend_calculation_basis": "Based on X employees and Y revenue..."
}"""
    },
    {
        "id": "buying_signals_analyst",
        "name": "Buying Signals Analyst",
        "focus": "buying_signals",
        "prompt": """You are a buying signals analyst. Identify active buying signals and intent topics from:
- Technology stack changes (new tools indicate budget allocation)
- Job postings (hiring for specific roles indicates initiatives)
- Growth indicators
- Recent company changes
Output JSON: {
    "intent_topics": ["Topic 1", "Topic 2", "Topic 3"],
    "signal_strength": "low/medium/high/very_high",
    "buying_indicators": ["Indicator 1", "Indicator 2"],
    "technology_changes": ["Recent tech adoptions or changes"]
}"""
    },
    {
        "id": "scoops_analyst",
        "name": "Scoops & Triggers Analyst",
        "focus": "scoops",
        "prompt": """You are a corporate intelligence analyst. Identify recent scoops and trigger events:
- Executive hires (new leaders often bring new vendor preferences)
- Funding rounds (new capital means new spending)
- Expansions (new markets indicate expanded infrastructure needs)
- M&A activity (org changes indicate integration/consolidation needs)
For each scoop, provide: type, title, date (if known), and a brief description.
Output JSON: {
    "scoops": [
        {"type": "executive_hire/funding/expansion/ma", "title": "...", "date": "YYYY-MM-DD or null", "details": "..."}
    ],
    "trigger_summary": "1-2 sentence summary of key triggers"
}"""
    },
    {
        "id": "opportunity_themes_analyst",
        "name": "Opportunity Themes Analyst",
        "focus": "opportunity_themes",
        "prompt": """You are a sales opportunity analyst. Map organizational challenges to solution categories:
- Identify 2-4 key business/technology challenges based on company context
- Map each challenge to relevant solution categories
- Provide value proposition hooks
Output JSON: {
    "opportunity_themes": [
        {"challenge": "Challenge description", "solution_category": "Category", "value_proposition": "How to position"}
    ],
    "organizational_challenges": ["Challenge 1", "Challenge 2"],
    "solution_categories": ["Category 1", "Category 2"]
}"""
    },
    {
        "id": "stakeholder_bio_writer",
        "name": "Stakeholder Bio Writer",
        "focus": "stakeholder_profiles",
        "prompt": """You are an executive profile writer. For each stakeholder provided, create:
- A 2-3 sentence professional bio based on their role and company context
- Strategic priorities typical for their role (CIO=digital transformation, CTO=tech innovation, etc.)
- Communication style recommendation (data-driven, vision-focused, ROI-focused, etc.)
- Recommended approach for engaging them
Output JSON: {
    "stakeholder_profiles": [
        {
            "role_type": "CIO/CTO/CISO/COO/CFO/CPO",
            "bio": "2-3 sentence bio...",
            "strategic_priorities": ["Priority 1", "Priority 2", "Priority 3"],
            "communication_preference": "data-driven/vision-focused/ROI-focused/risk-focused",
            "recommended_approach": "How to engage this stakeholder..."
        }
    ]
}"""
    },
    {
        "id": "sales_program_strategist",
        "name": "Sales Program Strategist",
        "focus": "sales_strategy",
        "prompt": """You are a sales strategist. Based on the buying signals and company context, determine:
- Intent level: "Low" (early curiosity), "Medium" (problem acknowledgement), "High" (active evaluation), "Very High" (decision stage)
- Strategy recommendation based on intent level
- Key talking points per stakeholder type
- Timing recommendation
Output JSON: {
    "intent_level": "Low/Medium/High/Very High",
    "intent_score": 0.0-1.0,
    "strategy_text": "Strategy recommendation...",
    "timing_recommendation": "When to engage...",
    "stakeholder_strategies": {
        "CIO": "Approach for CIO...",
        "CTO": "Approach for CTO...",
        "CFO": "Approach for CFO..."
    }
}"""
    },
    {
        "id": "tech_stack_categorizer",
        "name": "Technology Stack Categorizer",
        "focus": "tech_stack_categories",
        "prompt": """You are a technology analyst. Categorize the company's technology stack into standard categories:
- CRM (e.g., Salesforce, HubSpot)
- Marketing Automation (e.g., Marketo, Pardot)
- Sales Tools (e.g., Outreach, Gong)
- Infrastructure (e.g., AWS, Azure, GCP)
- Analytics (e.g., Tableau, Looker)
- Collaboration (e.g., Slack, Teams)
- Security (e.g., Okta, CrowdStrike)
- Other
Output JSON: {
    "technology_categories": {
        "crm": ["Tool1", "Tool2"],
        "marketing_automation": ["Tool1"],
        "sales_tools": ["Tool1"],
        "infrastructure": ["Tool1", "Tool2"],
        "analytics": ["Tool1"],
        "collaboration": ["Tool1"],
        "security": ["Tool1"],
        "other": ["Tool1"]
    },
    "tech_stack_summary": "Brief summary of tech maturity and notable tools"
}"""
    },
    {
        "id": "it_spend_estimator",
        "name": "IT Spend Estimator",
        "focus": "it_spend",
        "prompt": """You are an IT spending analyst. Estimate annual IT spend based on:
- Employee count (larger = more IT spend)
- Annual revenue (tech companies: 5-10% of revenue, others: 3-5%)
- Industry (tech/finance spend more)
- Known technology stack complexity
Provide a range estimate with confidence level.
Output JSON: {
    "estimated_it_spend_low": "$X million",
    "estimated_it_spend_high": "$Y million",
    "estimated_it_spend_display": "$X-$Y million",
    "spend_confidence": "low/medium/high",
    "calculation_basis": "How you calculated this...",
    "spend_breakdown": {
        "infrastructure": "XX%",
        "software": "XX%",
        "services": "XX%"
    }
}"""
    },
    {
        "id": "news_intelligence_analyst",
        "name": "News Intelligence Analyst",
        "focus": "news_intelligence",
        "prompt": """You are a news intelligence analyst. Analyze recent company news to extract actionable sales intelligence:

From the news data provided, identify and summarize:
1. EXECUTIVE CHANGES: New hires, departures, promotions (especially C-suite) - these indicate org changes and new priorities
2. FUNDING NEWS: Recent funding rounds, valuations, investor information - indicates growth capital and spending capacity
3. PARTNERSHIPS & M&A: Strategic partnerships, acquisitions, mergers - indicates strategic direction and integration needs
4. EXPANSION NEWS: New offices, market expansion, geographic growth - indicates infrastructure and scaling needs
5. PRODUCT LAUNCHES: New products, services, major updates - indicates innovation focus and potential tech needs

For each category, provide a clear summary suitable for sales intelligence briefings.

Output JSON: {
    "news_executive_changes": "Summary of executive changes and their implications for sales...",
    "news_funding": "Summary of funding news and spending implications...",
    "news_partnerships": "Summary of partnership/M&A activity and opportunities...",
    "news_expansions": "Summary of expansion news and infrastructure needs...",
    "news_product_launches": "Summary of product news and innovation focus...",
    "news_key_insights": ["Key insight 1", "Key insight 2", "Key insight 3"],
    "news_sales_implications": "Overall sales implications from recent news...",
    "news_timing_signals": "Best timing indicators from news for outreach..."
}"""
    },
]

# Aggregator prompt
AGGREGATOR_PROMPT = """You are the Chief Data Aggregator. You have received analyses from 29 specialist LLMs about a company.

Your job is to:
1. Synthesize all specialist inputs into a single, authoritative company profile with EXPANDED INTELLIGENCE
2. Resolve any conflicts by choosing the most specific/accurate data
3. BE CONCISE AND FACT-DRIVEN - no verbose language
4. List specifics instead of generalizations (e.g., list actual country names, not "operates globally")
5. Use actual numbers, not ranges when possible
6. Remove any fluff or marketing language
7. INTEGRATE NEWS DATA: Use recent news to inform buying signals, scoops, and sales strategy
8. PERSPECTIVE: You are analyzing this company from the perspective of HP trying to sell to them

CRITICAL OUTPUT RULES:
- CAPITALIZATION: Use Proper Title Case for all names (company names, person names, cities, countries, industries)
- geographic_reach: List actual country names with proper capitalization (max 20)
- employee_count: Use a number or specific range
- annual_revenue: Use specific figures like "$198.3 billion" or "$50M-$100M"
- ceo: Full name with proper capitalization
- target_market: List specific segments
- technologies: List actual tech names
- NEWS INTEGRATION: Recent news should directly influence buying_signals.scoops and sales timing
- PARAGRAPHS: For detailed fields, provide substantive 2-4 sentence paragraphs, not one-liners

Output a clean JSON object with BOTH original and EXPANDED fields:
{{
    "company_name": "Proper Case Name",
    "domain": "example.com",
    "industry": "Proper Case Industry",
    "sub_industry": "Proper Case Sub-Industry",
    "employee_count": number or "X-Y",
    "annual_revenue": "$X billion/million or range",
    "headquarters": "City, State, Country",
    "geographic_reach": ["United States", "United Kingdom", ...],
    "founded_year": number,
    "founders": ["First Last", "First Last"],
    "ceo": "First Last",
    "target_market": "B2B/B2C/B2G",
    "customer_segments": ["Segment1", "Segment2"],
    "products": ["Product1", "Product2"],
    "technologies": ["Tech1", "Tech2"],
    "competitors": ["Competitor1", "Competitor2"],
    "company_type": "Public/Private/Subsidiary",
    "linkedin_url": "https://linkedin.com/company/...",
    "confidence_score": 0.0-1.0,

    "executive_snapshot": {{
        "account_name": "Company Name",
        "company_overview": "Detailed paragraph overview of the organization - who they are, what they do, their market position, and key differentiators",
        "account_type": "Public Sector/Private Sector",
        "company_classification": "Public/Private/Government",
        "estimated_it_spend": "$X-$Y million annually",
        "installed_technologies": [
            {{"name": "Salesforce", "category": "CRM", "last_seen": "2024-01"}}
        ]
    }},

    "buying_signals": {{
        "intent_topics_detailed": [
            {{"topic": "Cloud Migration", "description": "Detailed paragraph explaining their interest in this topic and specific indicators"}},
            {{"topic": "Security Enhancement", "description": "Detailed paragraph on security initiatives"}},
            {{"topic": "AI/ML Adoption", "description": "Detailed paragraph on AI initiatives"}}
        ],
        "interest_over_time": {{
            "technologies": [
                {{"name": "Cloud Computing", "score": 85, "trend": "increasing"}},
                {{"name": "Cybersecurity", "score": 78, "trend": "stable"}}
            ],
            "summary": "Paragraph summarizing their technology interest trends"
        }},
        "top_partner_mentions": ["Partner1", "Partner2", "Partner3"],
        "key_signals": {{
            "news_paragraphs": [
                "First paragraph based on recent news and what it indicates about buying readiness",
                "Second paragraph on another key news signal",
                "Third paragraph on additional signal"
            ],
            "implications": "Paragraph on what these signals mean for sales approach"
        }},
        "intent_topics": ["Topic 1", "Topic 2", "Topic 3"],
        "signal_strength": "low/medium/high/very_high",
        "scoops": [
            {{"type": "executive_hire/funding/expansion/merger_acquisition/product_launch", "title": "...", "date": "YYYY-MM-DD or null", "details": "..."}}
        ],
        "opportunity_themes": [
            {{"challenge": "...", "solution_category": "...", "value_proposition": "..."}}
        ]
    }},

    "opportunity_themes_detailed": {{
        "pain_points": [
            "First paragraph describing a specific pain point the company faces",
            "Second paragraph on another operational challenge",
            "Third paragraph on a strategic challenge"
        ],
        "sales_opportunities": [
            "First paragraph on where HP can provide value",
            "Second paragraph on another sales opportunity",
            "Third paragraph on additional opportunity"
        ],
        "recommended_solution_areas": [
            "First paragraph recommending a solution area based on pain points",
            "Second paragraph on another solution recommendation",
            "Third paragraph on additional solution area"
        ]
    }},

    "news_intelligence": {{
        "executive_changes": "Summary of recent executive hires/departures from news",
        "funding_news": "Summary of recent funding/investment news",
        "partnership_news": "Summary of recent partnerships/M&A from news",
        "expansion_news": "Summary of recent expansion/growth news",
        "key_insights": ["Actionable insight 1 from news", "Actionable insight 2"],
        "sales_implications": "How recent news affects sales approach",
        "articles_analyzed": number
    }},

    "technology_stack": {{
        "crm": ["Tool1"],
        "marketing_automation": ["Tool1"],
        "sales_tools": ["Tool1"],
        "infrastructure": ["Tool1"],
        "analytics": ["Tool1"],
        "collaboration": ["Tool1"],
        "security": ["Tool1"],
        "other": ["Tool1"]
    }},

    "stakeholder_profiles": {{
        "CIO": {{
            "bio": "1 paragraph bio - if they are a new hire, call out and include the date",
            "strategic_priorities": [
                {{"priority": "Priority 1", "description": "Description of this priority"}},
                {{"priority": "Priority 2", "description": "Description"}},
                {{"priority": "Priority 3", "description": "Description"}}
            ],
            "communication_preference": "Email/LinkedIn/Phone/Events",
            "conversation_starters": "1-2 sentences of persona-tailored conversation openers",
            "recommended_next_steps": [
                "Introduce emerging trends and thought leadership to build awareness",
                "Highlight business challenges and frame HP solutions as ways to address them",
                "Reinforce proof points with case studies and demonstrate integration value",
                "Emphasize ROI, deployment support, and ease of scaling with HP solutions"
            ]
        }},
        "CTO": {{ "bio": "...", "strategic_priorities": [...], "communication_preference": "...", "conversation_starters": "...", "recommended_next_steps": [...] }},
        "CISO": {{ "bio": "...", "strategic_priorities": [...], "communication_preference": "...", "conversation_starters": "...", "recommended_next_steps": [...] }},
        "CFO": {{ "bio": "...", "strategic_priorities": [...], "communication_preference": "...", "conversation_starters": "...", "recommended_next_steps": [...] }},
        "COO": {{ "bio": "...", "strategic_priorities": [...], "communication_preference": "...", "conversation_starters": "...", "recommended_next_steps": [...] }},
        "CPO": {{ "bio": "...", "strategic_priorities": [...], "communication_preference": "...", "conversation_starters": "...", "recommended_next_steps": [...] }}
    }},

    "supporting_assets": {{
        "contacts": [
            {{
                "role": "CIO",
                "name": "Executive Name",
                "email_template": "Subject and body of personalized email template for this contact",
                "linkedin_outreach": "Personalized LinkedIn connection request/message",
                "call_script": "Opening and key talking points for a phone call"
            }}
        ]
    }},

    "sales_program": {{
        "intent_level": "Low/Medium/High/Very High",
        "intent_score": 0.0-1.0,
        "strategy_text": "Sales strategy based on intent level and recent news"
    }}
}}

SPECIALIST INPUTS:
{specialist_inputs}

ORIGINAL DATA SOURCES:
Apollo.io: {apollo_data}
PeopleDataLabs: {pdl_data}
Hunter.io: {hunter_data}
ZoomInfo (PRIMARY): {zoominfo_data}
Stakeholders: {stakeholders_data}

CONFLICT RESOLUTION: When data sources disagree on a field (e.g., CEO name, headquarters, revenue),
ZoomInfo takes priority as the tiebreaker. Cross-reference all sources for accuracy.

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


async def run_specialist(specialist: Dict, company_data: Dict, apollo_data: Dict, pdl_data: Dict, hunter_data: Dict = None, stakeholders_data: List[Dict] = None, news_data: Dict = None, zoominfo_data: Dict = None) -> Dict[str, Any]:
    """Run a single specialist LLM."""
    stakeholders_text = ""
    if stakeholders_data:
        stakeholders_text = f"\nStakeholders (C-Suite Executives): {json.dumps(stakeholders_data, indent=2)}"

    hunter_text = ""
    if hunter_data:
        hunter_text = f"\nHunter.io Data: {json.dumps(hunter_data, indent=2)}"

    zoominfo_text = ""
    if zoominfo_data:
        zoominfo_text = f"\nZoomInfo Data (PRIMARY - use as tiebreaker when sources disagree): {json.dumps(zoominfo_data, indent=2)}"

    news_text = ""
    if news_data and news_data.get("success"):
        news_summaries = news_data.get("summaries", {})
        news_text = f"""\nRecent News (Last 90 Days):
- Executive Changes: {news_summaries.get('executive_hires', 'None')}
- Funding: {news_summaries.get('funding_news', 'None')}
- Partnerships: {news_summaries.get('partnership_news', 'None')}
- Expansions: {news_summaries.get('expansion_news', 'None')}"""

    data_context = f"""
Company: {company_data.get('company_name', 'Unknown')}
Domain: {company_data.get('domain', 'Unknown')}

Apollo.io Data: {json.dumps(apollo_data, indent=2) if apollo_data else 'No data'}

PeopleDataLabs Data: {json.dumps(pdl_data, indent=2) if pdl_data else 'No data'}
{hunter_text}
{zoominfo_text}
{stakeholders_text}
{news_text}

CONFLICT RESOLUTION: When Apollo and PDL disagree on a data point, ZoomInfo data takes priority as the tiebreaker.

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


async def run_council(company_data: Dict, apollo_data: Dict, pdl_data: Dict, hunter_data: Dict = None, stakeholders_data: List[Dict] = None, news_data: Dict = None, zoominfo_data: Dict = None) -> Dict[str, Any]:
    """
    Run the full LLM Council:
    1. Run specialists in batches of 5 to avoid rate limits
    2. Aggregate results with central LLM
    """
    logger.info(f"Starting LLM Council ({len(SPECIALISTS)} specialists) for {company_data.get('company_name')}")

    # Step 1: Run specialists in batches of 5 to avoid rate limits
    valid_results = []
    batch_size = 5

    for i in range(0, len(SPECIALISTS), batch_size):
        batch = SPECIALISTS[i:i + batch_size]
        logger.info(f"Running specialist batch {i//batch_size + 1}/{(len(SPECIALISTS) + batch_size - 1)//batch_size}")

        batch_tasks = [
            run_specialist(specialist, company_data, apollo_data, pdl_data, hunter_data, stakeholders_data, news_data, zoominfo_data)
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

    news_summary_text = "No news data"
    if news_data and news_data.get("success"):
        news_summaries = news_data.get("summaries", {})
        news_summary_text = f"""Recent News (Last 90 Days):
- Executive Changes: {news_summaries.get('executive_hires', 'None')}
- Funding: {news_summaries.get('funding_news', 'None')}
- Partnerships: {news_summaries.get('partnership_news', 'None')}
- Expansions: {news_summaries.get('expansion_news', 'None')}"""

    aggregator_prompt = AGGREGATOR_PROMPT.format(
        specialist_inputs=specialist_inputs_text,
        apollo_data=json.dumps(apollo_data, indent=2) if apollo_data else "No data",
        pdl_data=json.dumps(pdl_data, indent=2) if pdl_data else "No data",
        hunter_data=json.dumps(hunter_data, indent=2) if hunter_data else "No data",
        zoominfo_data=json.dumps(zoominfo_data, indent=2) if zoominfo_data else "No data",
        stakeholders_data=json.dumps(stakeholders_data, indent=2) if stakeholders_data else "No stakeholder data"
    ) + f"\n\nNEWS DATA:\n{news_summary_text}"

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


def extract_base_data(company_data: Dict, apollo_data: Dict, pdl_data: Dict, hunter_data: Dict = None, news_data: Dict = None, zoominfo_data: Dict = None) -> Dict[str, Any]:
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

    # Extract from Hunter.io data
    if hunter_data:
        if hunter_data.get("organization"):
            result["company_name"] = title_case_name(hunter_data["organization"])
        if hunter_data.get("country"):
            if not result.get("geographic_reach"):
                result["geographic_reach"] = []
            country = title_case_name(hunter_data["country"])
            if country not in result["geographic_reach"]:
                result["geographic_reach"].append(country)
        if hunter_data.get("industry"):
            result["industry"] = title_case_name(hunter_data["industry"])
        if hunter_data.get("twitter"):
            result["twitter"] = hunter_data["twitter"]
        if hunter_data.get("facebook"):
            result["facebook"] = hunter_data["facebook"]
        if hunter_data.get("linkedin"):
            result["linkedin_url"] = hunter_data["linkedin"]

        # Extract contact emails from Hunter.io
        emails = hunter_data.get("emails", [])
        if emails:
            # Store email contacts for potential stakeholder enrichment
            hunter_contacts = []
            for email in emails[:10]:  # Limit to top 10
                contact = {
                    "email": email.get("value"),
                    "first_name": email.get("first_name"),
                    "last_name": email.get("last_name"),
                    "position": email.get("position"),
                    "department": email.get("department"),
                    "confidence": email.get("confidence"),
                    "linkedin": email.get("linkedin"),
                    "twitter": email.get("twitter"),
                    "phone": email.get("phone_number")
                }
                if contact["email"]:
                    hunter_contacts.append(contact)
            if hunter_contacts:
                result["hunter_contacts"] = hunter_contacts

    # Extract from ZoomInfo data (PRIMARY SOURCE — overrides conflicting data)
    if zoominfo_data:
        if zoominfo_data.get("company_name"):
            result["company_name"] = title_case_name(zoominfo_data["company_name"])
        if zoominfo_data.get("industry"):
            result["industry"] = title_case_name(zoominfo_data["industry"])
        if zoominfo_data.get("employee_count"):
            result["employee_count"] = zoominfo_data["employee_count"]
        if zoominfo_data.get("revenue"):
            result["annual_revenue"] = zoominfo_data["revenue"]
        if zoominfo_data.get("headquarters"):
            result["headquarters"] = zoominfo_data["headquarters"]
        if zoominfo_data.get("founded_year"):
            result["founded_year"] = zoominfo_data["founded_year"]
        if zoominfo_data.get("ceo"):
            result["ceo"] = title_case_name(zoominfo_data["ceo"])
        if zoominfo_data.get("linkedin_url"):
            result["linkedin_url"] = zoominfo_data["linkedin_url"]
        # Growth metrics (ZoomInfo exclusive)
        if zoominfo_data.get("one_year_employee_growth"):
            result["one_year_employee_growth"] = zoominfo_data["one_year_employee_growth"]
        if zoominfo_data.get("two_year_employee_growth"):
            result["two_year_employee_growth"] = zoominfo_data["two_year_employee_growth"]
        if zoominfo_data.get("funding_amount"):
            result["funding_amount"] = zoominfo_data["funding_amount"]
        if zoominfo_data.get("fortune_rank"):
            result["fortune_rank"] = zoominfo_data["fortune_rank"]
        if zoominfo_data.get("num_locations"):
            result["num_locations"] = zoominfo_data["num_locations"]
        if zoominfo_data.get("business_model"):
            result["business_model"] = zoominfo_data["business_model"]
        # Intent signals
        if zoominfo_data.get("intent_signals"):
            result["intent_signals"] = zoominfo_data["intent_signals"]
        # Scoops
        if zoominfo_data.get("scoops"):
            result["scoops"] = zoominfo_data["scoops"]
        # Technology installs
        if zoominfo_data.get("technology_installs"):
            result["technology_installs"] = zoominfo_data["technology_installs"]

    # Extract news data summaries
    if news_data and news_data.get("success"):
        news_summaries = news_data.get("summaries", {})
        result["executive_hires"] = news_summaries.get("executive_hires", "No recent executive changes found")
        result["funding_news"] = news_summaries.get("funding_news", "No recent funding announcements found")
        result["partnership_news"] = news_summaries.get("partnership_news", "No recent partnership or acquisition news found")
        result["expansion_news"] = news_summaries.get("expansion_news", "No recent expansion news found")

        # Also store raw news categories for detailed view
        news_categories = news_data.get("categories", {})
        result["news_categories"] = {
            "executive_changes": news_categories.get("executive_changes", []),
            "funding": news_categories.get("funding", []),
            "partnerships": news_categories.get("partnerships", []),
            "expansions": news_categories.get("expansions", []),
            "products": news_categories.get("products", []),
            "financial": news_categories.get("financial", [])
        }
        result["news_articles_count"] = news_data.get("articles_count", 0)

    return result


def apply_formatting(data: Dict[str, Any]) -> Dict[str, Any]:
    """Apply proper formatting (capitalization, etc.) to the final output."""
    result = data.copy()

    # Fields that should have title case
    title_case_fields = [
        "company_name", "industry", "sub_industry", "headquarters",
        "ceo", "target_market", "company_type"
    ]

    for field in title_case_fields:
        if result.get(field) and isinstance(result[field], str):
            result[field] = title_case_name(result[field])

    # Handle list fields that should have title case
    list_title_case_fields = ["founders", "customer_segments", "geographic_reach", "competitors"]
    for field in list_title_case_fields:
        if result.get(field) and isinstance(result[field], list):
            result[field] = [title_case_name(item) if isinstance(item, str) else item for item in result[field]]

    # Ensure revenue has proper formatting
    if result.get("annual_revenue"):
        revenue = result["annual_revenue"]
        if isinstance(revenue, str):
            # Make sure it starts with $ if it's a monetary value
            if revenue and revenue[0].isdigit():
                result["annual_revenue"] = f"${revenue}"
        elif isinstance(revenue, (int, float)):
            # Format large numbers
            if revenue >= 1_000_000_000:
                result["annual_revenue"] = f"${revenue / 1_000_000_000:.1f} Billion"
            elif revenue >= 1_000_000:
                result["annual_revenue"] = f"${revenue / 1_000_000:.1f} Million"
            else:
                result["annual_revenue"] = f"${revenue:,.0f}"

    # News summaries are already added in extract_base_data, no need to add them here

    return result


async def validate_with_council(company_data: Dict, apollo_data: Dict, pdl_data: Dict, hunter_data: Dict = None, stakeholders_data: List[Dict] = None, news_data: Dict = None, zoominfo_data: Dict = None) -> Dict[str, Any]:
    """
    Main entry point for LLM Council validation.
    Returns validated, concise, fact-driven company data with expanded intelligence.
    Falls back to direct extraction if council fails.
    """
    # Always extract base data first as fallback
    base_data = extract_base_data(company_data, apollo_data, pdl_data, hunter_data, news_data, zoominfo_data)

    # Add stakeholder data to base_data if available
    if stakeholders_data:
        base_data["stakeholder_map"] = {
            "stakeholders": stakeholders_data,
            "data_quality": "complete" if len(stakeholders_data) >= 3 else "partial" if stakeholders_data else "minimal"
        }

    if not OPENAI_API_KEY:
        logger.warning("OpenAI not configured, using direct extraction")
        base_data["_council_metadata"] = {"specialists_run": 0, "specialists_total": len(SPECIALISTS), "mode": "direct_extraction"}
        return apply_formatting(base_data)

    try:
        result = await run_council(company_data, apollo_data, pdl_data, hunter_data, stakeholders_data, news_data, zoominfo_data)

        # Check if council returned useful data (more than just metadata)
        useful_fields = [k for k in result.keys() if not k.startswith("_") and result[k]]
        if len(useful_fields) < 3:
            logger.warning(f"Council returned minimal data ({len(useful_fields)} fields), using fallback")
            # Merge council result with base data, preferring council values
            merged = {**base_data, **{k: v for k, v in result.items() if v}}
            merged["confidence_score"] = 0.65
            return apply_formatting(merged)

        # Ensure we have minimum required fields by merging with base data
        for key, value in base_data.items():
            if key not in result or not result.get(key):
                result[key] = value

        # Always include stakeholder_map from base data if council didn't generate it
        if "stakeholder_map" not in result and base_data.get("stakeholder_map"):
            result["stakeholder_map"] = base_data["stakeholder_map"]

        if not result.get("confidence_score"):
            result["confidence_score"] = 0.8

        return apply_formatting(result)

    except Exception as e:
        logger.error(f"LLM Council error: {e}")
        # Return base data on failure
        base_data["confidence_score"] = 0.5
        base_data["_council_metadata"] = {"error": str(e), "specialists_run": 0, "mode": "fallback"}
        return apply_formatting(base_data)
