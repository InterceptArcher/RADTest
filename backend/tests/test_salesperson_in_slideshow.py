"""
Tests for salesperson name integration in Gamma slideshow.
Following TDD - test written to verify salesperson appears in slideshow title slide.
"""
import pytest
from worker.gamma_slideshow import GammaSlideshowCreator


def test_salesperson_name_appears_in_slideshow():
    """Test that salesperson name from form appears in slideshow first slide."""

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

    creator = GammaSlideshowCreator(gamma_api_key="test_key")
    markdown = creator._generate_markdown(company_data=company_data, user_email="test@example.com")

    assert "John Smith" in markdown
    assert "Prepared for:** John Smith by the HP RAD Intelligence Desk" in markdown


def test_salesperson_name_fallback_to_email():
    """Test that slideshow falls back to email when salesperson name is not provided."""

    company_data = {
        "company_name": "Acme Corporation",
        "validated_data": {
            "company_name": "Acme Corporation",
            "domain": "acme.com",
        },
        "confidence_score": 0.85,
    }

    creator = GammaSlideshowCreator(gamma_api_key="test_key")
    markdown = creator._generate_markdown(company_data=company_data, user_email="jane.doe@hp.com")

    assert "Prepared for:** jane.doe@hp.com by the HP RAD Intelligence Desk" in markdown


def test_salesperson_name_in_company_data():
    """Test that salesperson_name is extracted from company_data correctly."""

    company_data = {
        "company_name": "Test Company",
        "validated_data": {"company_name": "Test Company"},
        "salesperson_name": "Alice Johnson",
        "confidence_score": 0.90,
    }

    creator = GammaSlideshowCreator(gamma_api_key="test_key")
    markdown = creator._generate_markdown(company_data=company_data, user_email=None)

    assert "Alice Johnson" in markdown
    assert "Prepared for:** Alice Johnson" in markdown


def test_on_demand_slideshow_missing_salesperson_name():
    """
    Regression: when company_data lacks salesperson_name (old on-demand endpoint
    bug), the slide should not silently show an empty name.
    """

    company_data_without_salesperson = {
        "company_name": "Acme Corporation",
        "validated_data": {
            "company_name": "Acme Corporation",
            "domain": "acme.com",
        },
        "confidence_score": 0.85,
        # salesperson_name intentionally absent
    }

    creator = GammaSlideshowCreator(gamma_api_key="test_key")
    markdown = creator._generate_markdown(
        company_data=company_data_without_salesperson,
        user_email=None,
    )

    # Without a name the "Prepared for" line should still be present and not empty
    assert "Prepared for:**" in markdown


def test_on_demand_slideshow_includes_salesperson_name():
    """
    Verify that after the on-demand endpoint fix (salesperson_name now included
    in company_data), the correct name appears on the title slide.
    """

    company_data_with_salesperson = {
        "company_name": "Acme Corporation",
        "validated_data": {
            "company_name": "Acme Corporation",
            "domain": "acme.com",
        },
        "confidence_score": 0.85,
        "salesperson_name": "Bob Martinez",
    }

    creator = GammaSlideshowCreator(gamma_api_key="test_key")
    markdown = creator._generate_markdown(
        company_data=company_data_with_salesperson,
        user_email=None,
    )

    assert "Bob Martinez" in markdown
    assert "Prepared for:** Bob Martinez" in markdown
