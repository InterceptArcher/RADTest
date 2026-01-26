"""
Demo FastAPI application that works without external API keys.
Returns mock data for demonstration purposes.
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict
import asyncio
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# In-memory storage for demo mode
jobs_store: Dict[str, dict] = {}

# Create FastAPI app
app = FastAPI(
    title="RADTest Backend (Demo Mode)",
    description="Company intelligence profile generation API - Demo version with mock data",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Models
class CompanyProfileRequest(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=500)
    domain: str = Field(..., min_length=1, max_length=255)
    industry: Optional[str] = Field(None, max_length=200)
    requested_by: str = Field(..., description="Email of requester")


class ProfileRequestResponse(BaseModel):
    status: str
    job_id: str
    message: Optional[str] = None


class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: Optional[int] = None
    current_step: Optional[str] = None
    result: Optional[dict] = None


# Health check
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "RADTest Backend Demo",
        "mode": "demo"
    }


# Root endpoint
@app.get("/", tags=["Info"])
async def root():
    """Root endpoint."""
    return {
        "service": "RADTest Backend Demo",
        "version": "1.0.0",
        "mode": "demo",
        "note": "This is a demo version using mock data",
        "endpoints": {
            "health": "/health",
            "profile_request": "/profile-request",
            "job_status": "/job-status/{job_id}",
            "docs": "/docs"
        }
    }


# Profile request endpoint
@app.post(
    "/profile-request",
    response_model=ProfileRequestResponse,
    status_code=status.HTTP_200_OK,
    tags=["Profile"]
)
async def create_profile_request(profile_request: CompanyProfileRequest):
    """
    Accept company profile requests and return mock job ID.

    In demo mode, this returns immediately with a mock job ID that encodes the company data.
    The actual data processing is simulated.
    """
    logger.info(f"Received profile request for: {profile_request.company_name}")

    # Encode company data in job_id (base64 encoded JSON)
    import base64
    import json

    company_data = {
        "company_name": profile_request.company_name,
        "domain": profile_request.domain,
        "industry": profile_request.industry or "Technology"
    }

    encoded_data = base64.urlsafe_b64encode(json.dumps(company_data).encode()).decode()
    job_id = f"demo-{encoded_data}"

    # Also store in memory as backup (though it may not persist on serverless)
    jobs_store[job_id] = company_data

    return ProfileRequestResponse(
        status="success",
        job_id=job_id,
        message="Profile request submitted successfully (demo mode)"
    )


# Job status endpoint
@app.get("/job-status/{job_id}", response_model=JobStatus, tags=["Status"])
async def get_job_status(job_id: str):
    """
    Get job status - returns mock completed data.

    In demo mode, this always returns a completed job with mock data.
    """
    logger.info(f"Status check for job: {job_id}")

    # Decode company data from job_id
    import base64
    import json

    company_data = None

    # Try to decode from job_id
    if job_id.startswith("demo-"):
        try:
            encoded_data = job_id.replace("demo-", "")
            decoded_json = base64.urlsafe_b64decode(encoded_data.encode()).decode()
            company_data = json.loads(decoded_json)
        except Exception as e:
            logger.warning(f"Failed to decode job_id: {e}")
            # Fall back to stored data
            company_data = jobs_store.get(job_id)

    # Use defaults if no data found
    if not company_data:
        company_data = {
            "company_name": "Demo Company",
            "domain": "demo.com",
            "industry": "Technology"
        }

    company_name = company_data.get("company_name", "Demo Company")
    domain = company_data.get("domain", "demo.com")
    industry = company_data.get("industry", "Technology")

    # Generate industry-specific mock data
    industry_lower = industry.lower()

    # Industry-specific templates
    if "tech" in industry_lower or "software" in industry_lower or "saas" in industry_lower:
        mock_data = {
            "employee_count": "500-2000",
            "revenue": "$50M - $200M",
            "headquarters": "San Francisco, CA",
            "founded_year": 2012,
            "ceo": "Tech Executive",
            "technology": ["Python", "React", "PostgreSQL", "AWS", "Kubernetes"],
            "target_market": "Enterprise SaaS",
            "geographic_reach": "Global"
        }
    elif "automotive" in industry_lower or "auto" in industry_lower:
        mock_data = {
            "employee_count": "10000-50000",
            "revenue": "$5B - $20B",
            "headquarters": "Detroit, MI",
            "founded_year": 2003,
            "ceo": "Automotive CEO",
            "technology": ["Electric Vehicles", "Autonomous Driving", "Battery Tech", "AI"],
            "target_market": "Consumer Automotive",
            "geographic_reach": "Global"
        }
    elif "finance" in industry_lower or "fintech" in industry_lower or "banking" in industry_lower:
        mock_data = {
            "employee_count": "5000-15000",
            "revenue": "$1B - $5B",
            "headquarters": "New York, NY",
            "founded_year": 2010,
            "ceo": "Finance Executive",
            "technology": ["Blockchain", "Mobile Banking", "AI/ML", "Cloud Infrastructure"],
            "target_market": "Financial Services",
            "geographic_reach": "North America & Europe"
        }
    elif "healthcare" in industry_lower or "health" in industry_lower or "medical" in industry_lower:
        mock_data = {
            "employee_count": "2000-8000",
            "revenue": "$500M - $2B",
            "headquarters": "Boston, MA",
            "founded_year": 2008,
            "ceo": "Healthcare Executive",
            "technology": ["EMR Systems", "Telemedicine", "AI Diagnostics", "Cloud Security"],
            "target_market": "Healthcare Providers",
            "geographic_reach": "United States"
        }
    elif "retail" in industry_lower or "ecommerce" in industry_lower or "e-commerce" in industry_lower:
        mock_data = {
            "employee_count": "15000-50000",
            "revenue": "$10B - $30B",
            "headquarters": "Seattle, WA",
            "founded_year": 2005,
            "ceo": "Retail Executive",
            "technology": ["E-commerce Platform", "Logistics Tech", "AI Recommendations", "Mobile Apps"],
            "target_market": "Online Retail",
            "geographic_reach": "Global"
        }
    elif "entertainment" in industry_lower or "media" in industry_lower or "streaming" in industry_lower:
        mock_data = {
            "employee_count": "8000-15000",
            "revenue": "$20B - $30B",
            "headquarters": "Los Angeles, CA",
            "founded_year": 1997,
            "ceo": "Media Executive",
            "technology": ["Streaming Platform", "Content Delivery Network", "AI Recommendations", "Video Encoding"],
            "target_market": "Consumer Entertainment",
            "geographic_reach": "Global - 190+ countries"
        }
    elif "aerospace" in industry_lower or "space" in industry_lower:
        mock_data = {
            "employee_count": "5000-12000",
            "revenue": "$2B - $10B",
            "headquarters": "Hawthorne, CA",
            "founded_year": 2002,
            "ceo": "Aerospace CEO",
            "technology": ["Rocket Propulsion", "Satellite Tech", "Reusable Vehicles", "Advanced Materials"],
            "target_market": "Commercial & Government Space",
            "geographic_reach": "Global"
        }
    else:
        # Default for unknown industries
        mock_data = {
            "employee_count": "1000-5000",
            "revenue": "$100M - $500M",
            "headquarters": "San Francisco, CA",
            "founded_year": 2010,
            "ceo": "Chief Executive Officer",
            "technology": ["Cloud Computing", "Data Analytics", "Mobile Apps", "AI/ML"],
            "target_market": "Enterprise",
            "geographic_reach": "Global"
        }

    # Simulate completed job with industry-appropriate mock data
    return JobStatus(
        job_id=job_id,
        status="completed",
        progress=100,
        current_step="Complete",
        result={
            "success": True,
            "company_name": company_name,
            "domain": domain,
            "slideshow_url": f"https://gamma.app/docs/{domain.replace('.', '-')}-profile",
            "confidence_score": 0.85,
            "validated_data": {
                "company_name": company_name,
                "domain": domain,
                "industry": industry,
                **mock_data,
                "contacts": {
                    "website": domain,
                    "linkedin": f"https://linkedin.com/company/{company_name.lower().replace(' ', '-')}",
                    "email": f"contact@{domain}"
                }
            }
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
