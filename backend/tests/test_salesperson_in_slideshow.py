"""
Tests for salesperson name integration in Gamma slideshow.
Following TDD - test written to verify salesperson appears in slideshow title slide.
"""
import pytest
from unittest.mock import Mock, patch
from worker.gamma_slideshow import GammaSlideshowCreator


@pytest.mark.asyncio
async def test_salesperson_name_appears_in_slideshow():
    """Test that salesperson name from form appears in slideshow first slide."""

    # Arrange: Create test data with salesperson name
    company_data = {
        "company_name": "Acme Corporation",
        "validated_data": {
            "company_name": "Acme Corporation",
            "domain": "acme.com",
            "salesperson_name": "John Smith",
        },
        "salesperson_name": "John Smith",
        "confidence_score": 0.85,
    }

    # Create Gamma slideshow creator
    creator = GammaSlideshowCreator(gamma_api_key="test_key")

    # Act: Generate markdown for slideshow
    markdown = await creator._generate_template_markdown(
        company_data=company_data,
        user_email="test@example.com"
    )

    # Assert: Verify salesperson name appears in the "Prepared for" line
    assert "Prepared for:** John Smith by the HP RAD Intelligence Desk" in markdown
    assert "John Smith" in markdown


@pytest.mark.asyncio
async def test_salesperson_name_fallback_to_email():
    """Test that slideshow falls back to email when salesperson name is not provided."""

    # Arrange: Create test data WITHOUT salesperson name
    company_data = {
        "company_name": "Acme Corporation",
        "validated_data": {
            "company_name": "Acme Corporation",
            "domain": "acme.com",
        },
        "confidence_score": 0.85,
    }

    # Create Gamma slideshow creator
    creator = GammaSlideshowCreator(gamma_api_key="test_key")

    # Act: Generate markdown for slideshow
    markdown = await creator._generate_template_markdown(
        company_data=company_data,
        user_email="jane.doe@hp.com"
    )

    # Assert: Verify email is used when salesperson name is not provided
    assert "Prepared for:** jane.doe@hp.com by the HP RAD Intelligence Desk" in markdown


@pytest.mark.asyncio
async def test_salesperson_name_in_company_data():
    """Test that salesperson_name is extracted from company_data correctly."""

    # Arrange
    company_data = {
        "company_name": "Test Company",
        "validated_data": {
            "company_name": "Test Company",
        },
        "salesperson_name": "Alice Johnson",
        "confidence_score": 0.90,
    }

    creator = GammaSlideshowCreator(gamma_api_key="test_key")

    # Act
    markdown = await creator._generate_template_markdown(
        company_data=company_data,
        user_email=None
    )

    # Assert: Salesperson name from company_data is used
    assert "Alice Johnson" in markdown
    assert "Prepared for:** Alice Johnson" in markdown
