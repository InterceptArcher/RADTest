"""
Railway worker service client.
Handles communication with Railway worker API.
"""
import httpx
import logging
from typing import Dict, Any
from ..config import settings

logger = logging.getLogger(__name__)


class RailwayClientError(Exception):
    """Custom exception for Railway client errors."""
    pass


async def forward_to_worker(company_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Forward company profile request to Railway worker service.

    Args:
        company_data: Dictionary containing company information

    Returns:
        Dictionary with job_id and status

    Raises:
        RailwayClientError: If the request fails
        ConnectionError: If network connection fails

    Note:
        This function uses RAILWAY_WORKER_URL and RAILWAY_API_TOKEN from
        environment variables. These values must be provided via environment variables.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.railway_api_token}"
    }

    try:
        async with httpx.AsyncClient(timeout=settings.worker_timeout) as client:
            logger.info(f"Forwarding request for company: {company_data.get('company_name')}")

            response = await client.post(
                settings.railway_worker_url,
                json=company_data,
                headers=headers
            )

            response.raise_for_status()

            result = response.json()
            logger.info(f"Successfully forwarded request. Job ID: {result.get('job_id')}")

            return result

    except httpx.TimeoutException as e:
        logger.error(f"Timeout while forwarding to Railway worker: {e}")
        raise ConnectionError("Request to worker service timed out") from e

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from Railway worker: {e.response.status_code}")
        raise RailwayClientError(
            f"Worker service returned error: {e.response.status_code}"
        ) from e

    except httpx.RequestError as e:
        logger.error(f"Network error while contacting Railway worker: {e}")
        raise ConnectionError("Failed to connect to worker service") from e

    except Exception as e:
        logger.error(f"Unexpected error forwarding to Railway worker: {e}")
        raise RailwayClientError(f"Unexpected error: {str(e)}") from e


def forward_to_worker_sync(company_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Synchronous version of forward_to_worker for testing purposes.

    Args:
        company_data: Dictionary containing company information

    Returns:
        Dictionary with job_id and status

    Raises:
        RailwayClientError: If the request fails
        ConnectionError: If network connection fails
    """
    import httpx

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.railway_api_token}"
    }

    try:
        with httpx.Client(timeout=settings.worker_timeout) as client:
            logger.info(f"Forwarding request for company: {company_data.get('company_name')}")

            response = client.post(
                settings.railway_worker_url,
                json=company_data,
                headers=headers
            )

            response.raise_for_status()

            result = response.json()
            logger.info(f"Successfully forwarded request. Job ID: {result.get('job_id')}")

            return result

    except httpx.TimeoutException as e:
        logger.error(f"Timeout while forwarding to Railway worker: {e}")
        raise ConnectionError("Request to worker service timed out") from e

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from Railway worker: {e.response.status_code}")
        raise RailwayClientError(
            f"Worker service returned error: {e.response.status_code}"
        ) from e

    except httpx.RequestError as e:
        logger.error(f"Network error while contacting Railway worker: {e}")
        raise ConnectionError("Failed to connect to worker service") from e

    except Exception as e:
        logger.error(f"Unexpected error forwarding to Railway worker: {e}")
        raise RailwayClientError(f"Unexpected error: {str(e)}") from e
