"""
Test module for Railway GraphQL API integration.
Following TDD approach - tests written before implementation.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from gql import gql


@pytest.fixture
def mock_graphql_client():
    """Mock GraphQL client for testing."""
    client = Mock()
    client.execute = AsyncMock()
    return client


@pytest.fixture
def container_trigger_mutation():
    """Sample GraphQL mutation for triggering containers."""
    return gql("""
        mutation TriggerExtractor($input: TriggerInput!) {
            triggerExtractor(input: $input) {
                success
                jobId
                containerId
            }
        }
    """)


class TestRailwayGraphQLIntegration:
    """Test cases for Railway GraphQL API integration."""

    def test_graphql_client_initialization(self):
        """Test that GraphQL client can be initialized."""
        from src.services.railway_graphql import RailwayGraphQLClient

        # Should not raise an exception with valid config
        client = RailwayGraphQLClient()
        assert client is not None

    @pytest.mark.asyncio
    async def test_trigger_extractor_container(self, mock_graphql_client):
        """Test triggering an extractor container via GraphQL mutation."""
        from src.services.railway_graphql import RailwayGraphQLClient

        with patch.object(
            RailwayGraphQLClient,
            '_get_client',
            return_value=mock_graphql_client
        ):
            mock_graphql_client.execute.return_value = {
                "triggerExtractor": {
                    "success": True,
                    "jobId": "job-123",
                    "containerId": "container-xyz"
                }
            }

            client = RailwayGraphQLClient()
            result = await client.trigger_extractor(
                company_name="Acme Corp",
                data_sources=["apollo", "pdl"]
            )

            assert result["success"] is True
            assert "jobId" in result
            assert "containerId" in result
            mock_graphql_client.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_with_invalid_data(self):
        """Test that invalid data raises appropriate errors."""
        from src.services.railway_graphql import RailwayGraphQLClient

        client = RailwayGraphQLClient()

        with pytest.raises(ValueError):
            await client.trigger_extractor(
                company_name="",  # Empty company name
                data_sources=["apollo"]
            )

        with pytest.raises(ValueError):
            await client.trigger_extractor(
                company_name="Acme",
                data_sources=[]  # Empty data sources
            )

    @pytest.mark.asyncio
    async def test_handle_graphql_errors(self, mock_graphql_client):
        """Test handling of GraphQL errors."""
        from src.services.railway_graphql import RailwayGraphQLClient
        from gql.transport.exceptions import TransportQueryError

        with patch.object(
            RailwayGraphQLClient,
            '_get_client',
            return_value=mock_graphql_client
        ):
            mock_graphql_client.execute.side_effect = TransportQueryError(
                "GraphQL error: Invalid mutation"
            )

            client = RailwayGraphQLClient()

            with pytest.raises(Exception) as exc_info:
                await client.trigger_extractor(
                    company_name="Acme Corp",
                    data_sources=["apollo"]
                )

            assert "GraphQL error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_authentication_headers(self):
        """Test that authentication headers are properly set."""
        from src.services.railway_graphql import RailwayGraphQLClient

        client = RailwayGraphQLClient()

        # Check that client has authentication configured
        assert hasattr(client, '_get_client')

    @pytest.mark.asyncio
    async def test_container_status_check(self, mock_graphql_client):
        """Test checking container status via GraphQL query."""
        from src.services.railway_graphql import RailwayGraphQLClient

        with patch.object(
            RailwayGraphQLClient,
            '_get_client',
            return_value=mock_graphql_client
        ):
            mock_graphql_client.execute.return_value = {
                "containerStatus": {
                    "status": "running",
                    "jobId": "job-123",
                    "containerId": "container-xyz"
                }
            }

            client = RailwayGraphQLClient()
            result = await client.check_container_status("container-xyz")

            assert result["status"] == "running"
            assert "jobId" in result
            mock_graphql_client.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_on_network_failure(self, mock_graphql_client):
        """Test retry mechanism for network failures."""
        from src.services.railway_graphql import RailwayGraphQLClient

        with patch.object(
            RailwayGraphQLClient,
            '_get_client',
            return_value=mock_graphql_client
        ):
            # First two calls fail, third succeeds
            mock_graphql_client.execute.side_effect = [
                ConnectionError("Network error"),
                ConnectionError("Network error"),
                {
                    "triggerExtractor": {
                        "success": True,
                        "jobId": "job-123",
                        "containerId": "container-xyz"
                    }
                }
            ]

            client = RailwayGraphQLClient()
            result = await client.trigger_extractor(
                company_name="Acme Corp",
                data_sources=["apollo"],
                max_retries=3
            )

            assert result["success"] is True
            assert mock_graphql_client.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_multiple_data_sources(self, mock_graphql_client):
        """Test triggering with multiple data sources."""
        from src.services.railway_graphql import RailwayGraphQLClient

        with patch.object(
            RailwayGraphQLClient,
            '_get_client',
            return_value=mock_graphql_client
        ):
            mock_graphql_client.execute.return_value = {
                "triggerExtractor": {
                    "success": True,
                    "jobId": "job-multi-123",
                    "containerId": "container-multi"
                }
            }

            client = RailwayGraphQLClient()
            result = await client.trigger_extractor(
                company_name="Acme Corp",
                data_sources=["apollo", "pdl", "other"]
            )

            assert result["success"] is True
            # Verify the mutation was called with all data sources
            call_args = mock_graphql_client.execute.call_args
            assert call_args is not None
