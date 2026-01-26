"""
Demo FastAPI application that works without external API keys.
Returns mock data for demonstration purposes.
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
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

    In demo mode, this returns immediately with a mock job ID.
    The actual data processing is simulated.
    """
    logger.info(f"Received profile request for: {profile_request.company_name}")

    # Generate mock job ID
    import hashlib
    job_id = f"demo-{hashlib.md5(profile_request.company_name.encode()).hexdigest()[:12]}"

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

    # Simulate completed job with mock data
    return JobStatus(
        job_id=job_id,
        status="completed",
        progress=100,
        current_step="Complete",
        result={
            "success": True,
            "company_name": "Demo Company",
            "domain": "demo.com",
            "slideshow_url": "https://gamma.app/docs/demo-slideshow",
            "confidence_score": 0.85,
            "validated_data": {
                "company_name": "Demo Company",
                "domain": "demo.com",
                "industry": "Technology",
                "employee_count": "1000-5000",
                "revenue": "$100M - $500M",
                "headquarters": "San Francisco, CA",
                "founded_year": 2010,
                "ceo": "John Doe",
                "technology": ["Python", "React", "PostgreSQL", "AWS"],
                "target_market": "Enterprise B2B",
                "geographic_reach": "Global",
                "contacts": {
                    "website": "demo.com",
                    "linkedin": "https://linkedin.com/company/demo",
                    "email": "contact@demo.com"
                }
            }
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
