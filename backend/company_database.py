"""
Real company data database for fallback when APIs fail.
Data sourced from public information (Wikipedia, company websites, etc.)
"""

COMPANY_DATABASE = {
    "microsoft": {
        "company_name": "Microsoft Corporation",
        "ceo": "Satya Nadella",
        "founded_year": 1975,
        "headquarters": "Redmond, Washington",
        "employee_count": "221,000",
        "revenue": "$211.9 billion (2023)",
        "industry": "Technology",
        "technology": ["Azure", "Windows", "Office 365", ".NET", "TypeScript", "GitHub"],
        "target_market": "Enterprise Software & Cloud Services",
        "geographic_reach": "Global - 190+ countries"
    },
    "apple": {
        "company_name": "Apple Inc.",
        "ceo": "Tim Cook",
        "founded_year": 1976,
        "headquarters": "Cupertino, California",
        "employee_count": "164,000",
        "revenue": "$394.3 billion (2023)",
        "industry": "Technology",
        "technology": ["iOS", "macOS", "Swift", "M-series chips", "ARKit"],
        "target_market": "Consumer Electronics & Services",
        "geographic_reach": "Global"
    },
    "google": {
        "company_name": "Google LLC (Alphabet Inc.)",
        "ceo": "Sundar Pichai",
        "founded_year": 1998,
        "headquarters": "Mountain View, California",
        "employee_count": "182,000",
        "revenue": "$307.4 billion (2023)",
        "industry": "Technology",
        "technology": ["Search", "Android", "Chrome", "Cloud", "AI/ML", "TensorFlow"],
        "target_market": "Search, Advertising & Cloud",
        "geographic_reach": "Global"
    },
    "amazon": {
        "company_name": "Amazon.com, Inc.",
        "ceo": "Andy Jassy",
        "founded_year": 1994,
        "headquarters": "Seattle, Washington",
        "employee_count": "1,541,000",
        "revenue": "$574.8 billion (2023)",
        "industry": "E-commerce & Cloud",
        "technology": ["AWS", "Alexa", "Lambda", "DynamoDB", "S3"],
        "target_market": "E-commerce & Cloud Services",
        "geographic_reach": "Global"
    },
    "meta": {
        "company_name": "Meta Platforms, Inc.",
        "ceo": "Mark Zuckerberg",
        "founded_year": 2004,
        "headquarters": "Menlo Park, California",
        "employee_count": "67,000",
        "revenue": "$134.9 billion (2023)",
        "industry": "Social Media & Technology",
        "technology": ["React", "PyTorch", "GraphQL", "React Native", "Llama AI"],
        "target_market": "Social Media & Advertising",
        "geographic_reach": "Global - 3+ billion users"
    },
    "facebook": {  # Alias for Meta
        "company_name": "Meta Platforms, Inc. (Facebook)",
        "ceo": "Mark Zuckerberg",
        "founded_year": 2004,
        "headquarters": "Menlo Park, California",
        "employee_count": "67,000",
        "revenue": "$134.9 billion (2023)",
        "industry": "Social Media & Technology",
        "technology": ["React", "PyTorch", "GraphQL", "React Native"],
        "target_market": "Social Media & Advertising",
        "geographic_reach": "Global - 3+ billion users"
    },
    "tesla": {
        "company_name": "Tesla, Inc.",
        "ceo": "Elon Musk",
        "founded_year": 2003,
        "headquarters": "Austin, Texas",
        "employee_count": "127,855",
        "revenue": "$96.8 billion (2023)",
        "industry": "Automotive & Energy",
        "technology": ["Electric Vehicles", "Autopilot", "Battery Tech", "Solar", "AI"],
        "target_market": "Electric Vehicles & Clean Energy",
        "geographic_reach": "Global"
    },
    "netflix": {
        "company_name": "Netflix, Inc.",
        "ceo": "Ted Sarandos & Greg Peters",
        "founded_year": 1997,
        "headquarters": "Los Gatos, California",
        "employee_count": "13,000",
        "revenue": "$33.7 billion (2023)",
        "industry": "Entertainment & Streaming",
        "technology": ["Streaming Platform", "CDN", "Recommendation AI", "Video Encoding"],
        "target_market": "Streaming Entertainment",
        "geographic_reach": "Global - 190+ countries"
    },
    "spacex": {
        "company_name": "Space Exploration Technologies Corp. (SpaceX)",
        "ceo": "Elon Musk",
        "founded_year": 2002,
        "headquarters": "Hawthorne, California",
        "employee_count": "13,000",
        "revenue": "$9 billion (2023 est.)",
        "industry": "Aerospace",
        "technology": ["Falcon 9", "Starship", "Starlink", "Raptor Engines"],
        "target_market": "Commercial & Government Space",
        "geographic_reach": "Global"
    },
    "stripe": {
        "company_name": "Stripe, Inc.",
        "ceo": "Patrick Collison",
        "founded_year": 2010,
        "headquarters": "San Francisco, California",
        "employee_count": "8,000",
        "revenue": "$14 billion (2023 est.)",
        "industry": "Fintech",
        "technology": ["Payment Processing", "APIs", "Fraud Detection", "Financial Infrastructure"],
        "target_market": "Online Payment Processing",
        "geographic_reach": "Global - 46 countries"
    },
    "openai": {
        "company_name": "OpenAI",
        "ceo": "Sam Altman",
        "founded_year": 2015,
        "headquarters": "San Francisco, California",
        "employee_count": "1,500",
        "revenue": "$2 billion (2023 est.)",
        "industry": "Artificial Intelligence",
        "technology": ["GPT-4", "ChatGPT", "DALL-E", "Whisper", "Deep Learning"],
        "target_market": "AI Research & Products",
        "geographic_reach": "Global"
    },
    "nvidia": {
        "company_name": "NVIDIA Corporation",
        "ceo": "Jensen Huang",
        "founded_year": 1993,
        "headquarters": "Santa Clara, California",
        "employee_count": "29,600",
        "revenue": "$60.9 billion (2024)",
        "industry": "Technology & Semiconductors",
        "technology": ["GPUs", "CUDA", "AI Chips", "GeForce", "Data Center"],
        "target_market": "AI & Graphics Processing",
        "geographic_reach": "Global"
    },
    "airbnb": {
        "company_name": "Airbnb, Inc.",
        "ceo": "Brian Chesky",
        "founded_year": 2008,
        "headquarters": "San Francisco, California",
        "employee_count": "6,800",
        "revenue": "$9.9 billion (2023)",
        "industry": "Travel & Hospitality",
        "technology": ["Marketplace Platform", "AI Matching", "Payment Processing"],
        "target_market": "Short-term Rentals",
        "geographic_reach": "Global - 220+ countries"
    },
    "uber": {
        "company_name": "Uber Technologies, Inc.",
        "ceo": "Dara Khosrowshahi",
        "founded_year": 2009,
        "headquarters": "San Francisco, California",
        "employee_count": "32,800",
        "revenue": "$37.3 billion (2023)",
        "industry": "Transportation & Technology",
        "technology": ["Ride-hailing Platform", "Route Optimization", "Mapping", "AI"],
        "target_market": "Ride-sharing & Food Delivery",
        "geographic_reach": "Global - 70+ countries"
    },
    "salesforce": {
        "company_name": "Salesforce, Inc.",
        "ceo": "Marc Benioff",
        "founded_year": 1999,
        "headquarters": "San Francisco, California",
        "employee_count": "73,541",
        "revenue": "$34.9 billion (2024)",
        "industry": "Enterprise Software",
        "technology": ["CRM", "Cloud Computing", "AI (Einstein)", "Salesforce Platform"],
        "target_market": "Enterprise CRM & Cloud",
        "geographic_reach": "Global"
    },
    "oracle": {
        "company_name": "Oracle Corporation",
        "ceo": "Safra Catz",
        "founded_year": 1977,
        "headquarters": "Austin, Texas",
        "employee_count": "164,000",
        "revenue": "$52.9 billion (2024)",
        "industry": "Enterprise Software",
        "technology": ["Database", "Cloud Infrastructure", "Java", "MySQL"],
        "target_market": "Enterprise Database & Cloud",
        "geographic_reach": "Global"
    },
    "ibm": {
        "company_name": "International Business Machines Corporation",
        "ceo": "Arvind Krishna",
        "founded_year": 1911,
        "headquarters": "Armonk, New York",
        "employee_count": "282,100",
        "revenue": "$61.9 billion (2023)",
        "industry": "Technology & Consulting",
        "technology": ["Cloud", "AI (Watson)", "Quantum Computing", "Mainframes"],
        "target_market": "Enterprise IT & Consulting",
        "geographic_reach": "Global"
    }
}


def get_company_data(company_name: str, domain: str, industry: str = "") -> dict:
    """
    Get real company data from database.
    Searches by company name and domain.
    """
    # Normalize search key
    search_key = company_name.lower().replace(" ", "").replace(",", "").replace(".", "").replace("inc", "").replace("corp", "").replace("llc", "")

    # Try direct match
    for key in COMPANY_DATABASE:
        if key in search_key or search_key in key:
            data = COMPANY_DATABASE[key].copy()
            data["confidence_score"] = 0.95
            return data

    # Try domain match
    domain_name = domain.lower().split('.')[0]
    if domain_name in COMPANY_DATABASE:
        data = COMPANY_DATABASE[domain_name].copy()
        data["confidence_score"] = 0.95
        return data

    # Return None if not found
    return None
