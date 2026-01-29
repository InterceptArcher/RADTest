"""
FastAPI main application for RADTest backend.
Handles profile requests and coordinates with Railway workers.
"""
from typing import List, Optional
from fastapi import FastAPI, Request, HTTPException, status, Query, Response
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
import sys

from .models.profile import (
    CompanyProfileRequest,
    ProfileRequestResponse,
    ErrorResponse
)
from .models.debug import (
    DebugData,
    ProcessStep,
    APIResponseData,
    LLMThoughtProcess,
    ProcessFlow,
)
from .services.railway_client import (
    forward_to_worker,
    RailwayClientError
)
from .services.debug_service import debug_service
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
            "debug_data": "/debug-data/{job_id}",
            "docs": "/docs"
        }
    }


# ============================================================================
# Debug Mode Endpoints (Features 018-021)
# ============================================================================

@app.get(
    "/debug-data/{job_id}",
    response_model=DebugData,
    tags=["Debug"],
    responses={
        200: {"description": "Debug data retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Job not found"},
        403: {"model": ErrorResponse, "description": "Unauthorized access"},
    }
)
async def get_debug_data(job_id: str):
    """
    Get complete debug data for a job.

    Feature 018: Debugging UI for Process Inspection

    Returns all debug information including:
    - Process steps with timing and status
    - API responses with masked sensitive data
    - LLM thought processes and decisions
    - Process flow visualization data

    Args:
        job_id: Unique job identifier

    Returns:
        Complete DebugData object
    """
    logger.info(f"Debug data requested for job: {job_id}")

    debug_data = debug_service.get_debug_data(job_id)

    if not debug_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Debug data not found for job"}
        )

    return debug_data


@app.head(
    "/debug-data/{job_id}",
    tags=["Debug"],
    responses={
        200: {"description": "Debug data available"},
        404: {"description": "Debug data not available"},
    }
)
async def check_debug_data_available(job_id: str, response: Response):
    """
    Check if debug data is available for a job.

    Returns 200 if available, 404 if not.
    """
    is_available = debug_service.check_debug_available(job_id)

    if not is_available:
        response.status_code = status.HTTP_404_NOT_FOUND

    return None


@app.get(
    "/debug-data/{job_id}/process-steps",
    response_model=List[ProcessStep],
    tags=["Debug"],
    responses={
        200: {"description": "Process steps retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Job not found"},
    }
)
async def get_process_steps(job_id: str):
    """
    Get process steps for a job.

    Feature 018: Debugging UI for Process Inspection

    Returns the pipeline steps with their status, timing, and metadata.

    Args:
        job_id: Unique job identifier

    Returns:
        List of ProcessStep objects
    """
    process_steps = debug_service.get_process_steps(job_id)

    if process_steps is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Process steps not found for job"}
        )

    return process_steps


@app.get(
    "/debug-data/{job_id}/api-responses",
    response_model=List[APIResponseData],
    tags=["Debug"],
    responses={
        200: {"description": "API responses retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Job not found"},
    }
)
async def get_api_responses(
    job_id: str,
    mask_sensitive: bool = Query(
        default=True,
        description="Whether to mask sensitive data in responses"
    )
):
    """
    Get API responses for a job.

    Feature 019: Display API Return Values

    Returns all API responses with optional sensitive data masking.
    Sensitive fields like API keys and tokens are masked by default.

    Args:
        job_id: Unique job identifier
        mask_sensitive: Whether to mask sensitive data (default: True)

    Returns:
        List of APIResponseData objects
    """
    api_responses = debug_service.get_api_responses(job_id, mask_sensitive)

    if api_responses is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "API responses not found for job"}
        )

    return api_responses


@app.get(
    "/debug-data/{job_id}/llm-processes",
    response_model=List[LLMThoughtProcess],
    tags=["Debug"],
    responses={
        200: {"description": "LLM thought processes retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Job not found"},
    }
)
async def get_llm_thought_processes(job_id: str):
    """
    Get LLM thought processes for a job.

    Feature 020: Display ChatGPT Thought Process

    Returns the decision-making insights and reasoning steps
    from LLM agents during data validation and conflict resolution.

    Args:
        job_id: Unique job identifier

    Returns:
        List of LLMThoughtProcess objects
    """
    llm_processes = debug_service.get_llm_thought_processes(job_id)

    if llm_processes is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "LLM thought processes not found for job"}
        )

    return llm_processes


@app.get(
    "/debug-data/{job_id}/process-flow",
    response_model=ProcessFlow,
    tags=["Debug"],
    responses={
        200: {"description": "Process flow retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Job not found"},
    }
)
async def get_process_flow(job_id: str):
    """
    Get process flow visualization data for a job.

    Feature 021: Visualize Process to Output Flow

    Returns nodes and edges for rendering a flowchart or timeline
    showing the process pipeline from request to output.

    Args:
        job_id: Unique job identifier

    Returns:
        ProcessFlow object with nodes and edges
    """
    process_flow = debug_service.get_process_flow(job_id)

    if process_flow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Process flow not found for job"}
        )

    return process_flow
