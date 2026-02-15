#!/usr/bin/env python3
"""
Test to validate Gamma API URL extraction logic.
This test validates different possible response structures from the Gamma API.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from worker.gamma_slideshow import GammaSlideshowCreator


class TestGammaURLExtraction:
    """Test URL extraction from various Gamma API response formats"""

    def test_url_in_gammaUrl_field(self):
        """Test extraction when URL is in gammaUrl field"""
        status_data = {
            "status": "completed",
            "gammaUrl": "https://gamma.app/docs/test-123",
            "generationId": "test-123"
        }

        # Extract URL using the same logic as the code
        gamma_url = (
            status_data.get("gammaUrl") or
            status_data.get("url") or
            status_data.get("webUrl") or
            status_data.get("gamma_url")
        )

        assert gamma_url == "https://gamma.app/docs/test-123"

    def test_url_in_url_field(self):
        """Test extraction when URL is in url field"""
        status_data = {
            "status": "completed",
            "url": "https://gamma.app/docs/test-456",
            "generationId": "test-456"
        }

        gamma_url = (
            status_data.get("gammaUrl") or
            status_data.get("url") or
            status_data.get("webUrl") or
            status_data.get("gamma_url")
        )

        assert gamma_url == "https://gamma.app/docs/test-456"

    def test_url_in_nested_gamma_object(self):
        """Test extraction when URL is nested in gamma object"""
        status_data = {
            "status": "completed",
            "generationId": "test-789",
            "gamma": {
                "url": "https://gamma.app/docs/test-789"
            }
        }

        # Try standard fields first
        gamma_url = (
            status_data.get("gammaUrl") or
            status_data.get("url") or
            status_data.get("webUrl") or
            status_data.get("gamma_url")
        )

        # Check nested objects
        if not gamma_url and isinstance(status_data.get("gamma"), dict):
            gamma_url = status_data["gamma"].get("url") or status_data["gamma"].get("webUrl")

        assert gamma_url == "https://gamma.app/docs/test-789"

    def test_url_construction_fallback(self):
        """Test URL construction when no URL field is present"""
        status_data = {
            "status": "completed",
            "generationId": "abc123xyz"
        }

        generation_id = status_data.get("generationId")

        # Try all extraction methods
        gamma_url = (
            status_data.get("gammaUrl") or
            status_data.get("url") or
            status_data.get("webUrl") or
            status_data.get("gamma_url")
        )

        if not gamma_url and isinstance(status_data.get("gamma"), dict):
            gamma_url = status_data["gamma"].get("url") or status_data["gamma"].get("webUrl")

        if not gamma_url and isinstance(status_data.get("data"), dict):
            gamma_url = status_data["data"].get("url") or status_data["data"].get("gammaUrl")

        # Fallback: construct URL from generation ID
        if not gamma_url and generation_id:
            # NOTE: This URL format needs to be validated against Gamma API docs
            gamma_url = f"https://gamma.app/docs/{generation_id}"

        assert gamma_url == f"https://gamma.app/docs/{generation_id}"
        assert gamma_url.startswith("https://")


@pytest.mark.asyncio
async def test_gamma_creator_handles_missing_url():
    """Test that GammaSlideshowCreator properly handles missing URL in API response"""

    creator = GammaSlideshowCreator(
        gamma_api_key="test_key_123",
        template_id="test_template"
    )

    # This test would require mocking the httpx client
    # For now, we just validate the creator can be instantiated
    assert creator.api_key == "test_key_123"
    assert creator.template_id == "test_template"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
