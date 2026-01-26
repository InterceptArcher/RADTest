"""
FastAPI main application for RADTest backend.
Handles profile requests and coordinates with Railway workers.
"""
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
import sys

from .models.profile import (
    CompanyProfileRequest,
    ProfileRequestResponse,
    ErrorResponse
)
from .services.railway_client import (
    forward_to_worker,
    RailwayClientError
)
from .config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Backend API for company profile data extraction",
    version="1.0.0"
)


# Request size limit middleware
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    """Middleware to enforce request size limits."""
    content_length = request.headers.get("content-length")

    if content_length and int(content_length) > settings.max_request_size:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={"error": "Request payload too large"}
        )

    return await call_next(request)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed messages."""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "error": "Invalid request data"
        }
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle value errors."""
    logger.error(f"Value error: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": str(exc)}
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": settings.app_name}


# Profile request endpoint
@app.post(
    "/profile-request",
    response_model=ProfileRequestResponse,
    status_code=status.HTTP_200_OK,
    tags=["Profile"],
    responses={
        200: {"description": "Request successfully submitted"},
        400: {"model": ErrorResponse, "description": "Invalid request format"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        413: {"model": ErrorResponse, "description": "Payload too large"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        503: {"model": ErrorResponse, "description": "Service unavailable"}
    }
)
async def create_profile_request(profile_request: CompanyProfileRequest):
    """
    Accept company profile requests and forward to Railway worker service.

    This endpoint:
    1. Validates incoming company data
    2. Formats the data as JSON
    3. Forwards to Railway worker service for processing

    Args:
        profile_request: Company profile request data

    Returns:
        ProfileRequestResponse with job_id and status

    Raises:
        HTTPException: For various error conditions
    """
    try:
        logger.info(
            f"Received profile request for company: {profile_request.company_name}"
        )

        # Convert to dict for forwarding
        company_data = profile_request.dict()

        # Forward to Railway worker service
        try:
            worker_response = await forward_to_worker(company_data)

            return ProfileRequestResponse(
                status=worker_response.get("status", "success"),
                job_id=worker_response.get("job_id", ""),
                message="Profile request submitted successfully"
            )

        except ConnectionError as e:
            logger.error(f"Network error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "Service unavailable",
                    "detail": "Unable to reach worker service"
                }
            )

        except RailwayClientError as e:
            logger.error(f"Railway client error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "Worker service error",
                    "detail": str(e)
                }
            )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        logger.error(f"Unexpected error in profile request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal server error",
                "detail": "An unexpected error occurred"
            }
        )


# Root endpoint
@app.get("/", tags=["Info"])
async def root():
    """Root endpoint with API information."""
    return {
        "service": settings.app_name,
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "profile_request": "/profile-request",
            "docs": "/docs"
        }
    }
