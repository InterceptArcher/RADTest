"""
Railway GraphQL API client for triggering extractor containers.
Uses gql library for GraphQL operations.
"""
import logging
import asyncio
from typing import Dict, Any, List, Optional
from gql import gql, Client
from gql.transport.httpx import HTTPXAsyncTransport
from gql.transport.exceptions import TransportQueryError

from ..config import settings

logger = logging.getLogger(__name__)


class RailwayGraphQLClient:
    """
    Client for interacting with Railway.app GraphQL API.

    This client handles:
    - Triggering extractor containers via mutations
    - Checking container status via queries
    - Retry logic for network failures
    - Proper authentication
    """

    def __init__(self):
        """
        Initialize Railway GraphQL client.

        Authentication token must be provided via RAILWAY_API_TOKEN
        environment variable.
        """
        self.endpoint = "https://backboard.railway.app/graphql/v2"
        self._client: Optional[Client] = None

    def _get_client(self) -> Client:
        """
        Get or create GraphQL client with authentication.

        Returns:
            Configured GQL client

        Note:
            RAILWAY_API_TOKEN must be provided via environment variables.
        """
        if self._client is None:
            transport = HTTPXAsyncTransport(
                url=self.endpoint,
                headers={
                    "Authorization": f"Bearer {settings.railway_api_token}",
                    "Content-Type": "application/json"
                },
                timeout=settings.worker_timeout
            )
            self._client = Client(
                transport=transport,
                fetch_schema_from_transport=False
            )

        return self._client

    async def trigger_extractor(
        self,
        company_name: str,
        data_sources: List[str],
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Trigger an extractor container for data extraction.

        Args:
            company_name: Name of the company to extract data for
            data_sources: List of data sources to use (e.g., ['apollo', 'pdl'])
            max_retries: Maximum number of retry attempts

        Returns:
            Dictionary with success status, jobId, and containerId

        Raises:
            ValueError: If input validation fails
            Exception: If GraphQL mutation fails after retries
        """
        # Validate inputs
        if not company_name or not company_name.strip():
            raise ValueError("company_name cannot be empty")

        if not data_sources or len(data_sources) == 0:
            raise ValueError("data_sources cannot be empty")

        # Define the mutation
        mutation = gql("""
            mutation TriggerExtractor($input: DeploymentTriggerInput!) {
                deploymentTrigger(input: $input) {
                    id
                }
            }
        """)

        # Prepare variables
        variables = {
            "input": {
                "projectId": settings.railway_project_id,
                "environmentId": settings.railway_environment_id,
                "serviceId": settings.railway_service_id
            }
        }

        # Retry logic
        last_error = None
        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Triggering extractor for {company_name} "
                    f"(attempt {attempt + 1}/{max_retries})"
                )

                client = self._get_client()

                async with client as session:
                    result = await session.execute(mutation, variable_values=variables)

                logger.info(
                    f"Successfully triggered extractor. "
                    f"Deployment ID: {result.get('deploymentTrigger', {}).get('id')}"
                )

                return {
                    "success": True,
                    "jobId": f"job-{result['deploymentTrigger']['id']}",
                    "containerId": result['deploymentTrigger']['id']
                }

            except ConnectionError as e:
                last_error = e
                logger.warning(
                    f"Network error on attempt {attempt + 1}: {e}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                continue

            except TransportQueryError as e:
                logger.error(f"GraphQL error: {e}")
                raise Exception(f"GraphQL error: {str(e)}") from e

            except Exception as e:
                logger.error(f"Unexpected error triggering extractor: {e}")
                raise

        # If we get here, all retries failed
        raise Exception(
            f"Failed to trigger extractor after {max_retries} attempts: {last_error}"
        )

    async def check_container_status(
        self,
        container_id: str
    ) -> Dict[str, Any]:
        """
        Check the status of a container.

        Args:
            container_id: ID of the container to check

        Returns:
            Dictionary with status information

        Raises:
            ValueError: If container_id is empty
            Exception: If GraphQL query fails
        """
        if not container_id or not container_id.strip():
            raise ValueError("container_id cannot be empty")

        # Define the query
        query = gql("""
            query GetDeploymentStatus($deploymentId: String!) {
                deployment(id: $deploymentId) {
                    id
                    status
                    createdAt
                }
            }
        """)

        variables = {
            "deploymentId": container_id
        }

        try:
            client = self._get_client()

            async with client as session:
                result = await session.execute(query, variable_values=variables)

            deployment = result.get("deployment", {})

            return {
                "status": deployment.get("status", "unknown"),
                "jobId": f"job-{deployment.get('id')}",
                "containerId": deployment.get("id"),
                "createdAt": deployment.get("createdAt")
            }

        except TransportQueryError as e:
            logger.error(f"GraphQL error checking status: {e}")
            raise Exception(f"GraphQL error: {str(e)}") from e

        except Exception as e:
            logger.error(f"Error checking container status: {e}")
            raise

    async def close(self):
        """Close the GraphQL client connection."""
        if self._client:
            await self._client.close_async()
            self._client = None
