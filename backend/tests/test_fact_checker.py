"""
Tests for Contact Fact Checker LLM.
TDD: Tests written FIRST before implementation.
"""
import pytest
import json
import os
import sys
from unittest.mock import AsyncMock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestFactCheckContacts:
    """Test LLM-based contact fact checking."""

    @pytest.mark.asyncio
    async def test_validates_correct_contacts(self):
        """Correct contacts get high fact_check_score."""
        from production_main import fact_check_contacts

        contacts = [
            {"name": "Satya Nadella", "title": "CEO", "email": "satya@microsoft.com"},
        ]

        mock_result = {
            "contacts": [
                {
                    "name": "Satya Nadella",
                    "fact_check_score": 0.95,
                    "fact_check_notes": "Verified: Satya Nadella is the CEO of Microsoft."
                }
            ]
        }

        with patch("production_main.OPENAI_API_KEY", "test-key"):
            with patch("production_main._call_openai_json", new_callable=AsyncMock,
                        return_value=mock_result):
                result = await fact_check_contacts("Microsoft", "microsoft.com", contacts)
                assert len(result) == 1
                assert result[0]["fact_check_score"] == 0.95

    @pytest.mark.asyncio
    async def test_filters_wrong_contacts(self):
        """Incorrect contacts with score < 0.3 are filtered out."""
        from production_main import fact_check_contacts

        contacts = [
            {"name": "Satya Nadella", "title": "CEO", "email": "satya@microsoft.com"},
            {"name": "Fake Person", "title": "CEO", "email": "fake@microsoft.com"},
        ]

        mock_result = {
            "contacts": [
                {"name": "Satya Nadella", "fact_check_score": 0.95,
                 "fact_check_notes": "Verified CEO"},
                {"name": "Fake Person", "fact_check_score": 0.1,
                 "fact_check_notes": "Not a known executive at Microsoft"},
            ]
        }

        with patch("production_main.OPENAI_API_KEY", "test-key"):
            with patch("production_main._call_openai_json", new_callable=AsyncMock,
                        return_value=mock_result):
                result = await fact_check_contacts("Microsoft", "microsoft.com", contacts)
                assert len(result) == 1
                assert result[0]["name"] == "Satya Nadella"

    @pytest.mark.asyncio
    async def test_handles_empty_contacts(self):
        """Returns empty list when no contacts provided."""
        from production_main import fact_check_contacts
        result = await fact_check_contacts("Microsoft", "microsoft.com", [])
        assert result == []

    @pytest.mark.asyncio
    async def test_handles_openai_failure_gracefully(self):
        """Returns original contacts when OpenAI fails."""
        from production_main import fact_check_contacts

        contacts = [
            {"name": "Test Person", "title": "CTO", "email": "test@co.com"},
        ]

        with patch("production_main.OPENAI_API_KEY", "test-key"):
            with patch("production_main._call_openai_json", new_callable=AsyncMock,
                        return_value=None):
                result = await fact_check_contacts("TestCo", "test.com", contacts)
                # Should return original contacts unchanged
                assert len(result) == 1
                assert result[0]["name"] == "Test Person"

    @pytest.mark.asyncio
    async def test_skips_when_no_openai_key(self):
        """Skips fact checking when OpenAI key not configured."""
        from production_main import fact_check_contacts

        contacts = [{"name": "Person", "title": "CEO"}]

        with patch("production_main.OPENAI_API_KEY", None):
            result = await fact_check_contacts("Co", "co.com", contacts)
            assert len(result) == 1
