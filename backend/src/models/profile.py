"""
Pydantic models for profile request data validation.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional


class CompanyProfileRequest(BaseModel):
    """
    Model for company profile request payload.
    Validates required fields for profile data extraction.
    """
    company_name: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Name of the company"
    )
    domain: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Company domain (e.g., example.com)"
    )
    industry: Optional[str] = Field(
        None,
        max_length=200,
        description="Industry sector"
    )
    requested_by: str = Field(
        ...,
        description="Email or ID of the requesting user"
    )

    @validator('domain')
    def validate_domain(cls, v):
        """Validate domain format."""
        if not v or len(v.strip()) == 0:
            raise ValueError('Domain cannot be empty')
        # Basic domain validation
        if ' ' in v:
            raise ValueError('Domain cannot contain spaces')
        return v.lower().strip()

    @validator('company_name')
    def validate_company_name(cls, v):
        """Validate company name."""
        if not v or len(v.strip()) == 0:
            raise ValueError('Company name cannot be empty')
        return v.strip()

    class Config:
        schema_extra = {
            "example": {
                "company_name": "Acme Corporation",
                "domain": "acme.com",
                "industry": "Technology",
                "requested_by": "user@example.com"
            }
        }


class ProfileRequestResponse(BaseModel):
    """
    Response model for successful profile request submission.
    """
    status: str = Field(
        ...,
        description="Status of the request (success/pending)"
    )
    job_id: str = Field(
        ...,
        description="Unique job identifier for tracking"
    )
    message: Optional[str] = Field(
        None,
        description="Additional information"
    )

    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "job_id": "job-abc-123",
                "message": "Profile request submitted successfully"
            }
        }


class ErrorResponse(BaseModel):
    """
    Response model for errors.
    """
    error: str = Field(
        ...,
        description="Error message"
    )
    detail: Optional[str] = Field(
        None,
        description="Detailed error information"
    )
