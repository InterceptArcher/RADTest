"""
Tests for IT budget estimate in Gamma slideshow.
TDD: Tests written FIRST — verifies _estimate_it_budget produces
real estimates instead of 'Contact for estimate' placeholder.
"""
import pytest


def test_it_budget_from_explicit_field():
    """Should use estimated_it_spend when available."""
    from worker.gamma_slideshow import GammaSlideshowCreator
    result = GammaSlideshowCreator._estimate_it_budget({
        "estimated_it_spend": "$5.0M - $10.0M annually"
    })
    assert "$5.0M" in result


def test_it_budget_from_employee_count_large():
    """Should estimate for large companies (>=50 employees → $M range)."""
    from worker.gamma_slideshow import GammaSlideshowCreator
    result = GammaSlideshowCreator._estimate_it_budget({
        "employee_count": 5000
    })
    assert "$" in result
    assert "M" in result
    assert "Contact" not in result
    assert "Not available" not in result


def test_it_budget_from_employee_count_small():
    """Should estimate for small companies (<50 employees → $K range)."""
    from worker.gamma_slideshow import GammaSlideshowCreator
    result = GammaSlideshowCreator._estimate_it_budget({
        "employee_count": 30
    })
    assert "$" in result
    assert "K" in result
    assert "Contact" not in result


def test_it_budget_from_employee_count_string():
    """Should handle employee count as comma-separated string."""
    from worker.gamma_slideshow import GammaSlideshowCreator
    result = GammaSlideshowCreator._estimate_it_budget({
        "employee_count": "2,500"
    })
    assert "$" in result
    assert "M" in result


def test_it_budget_no_data():
    """Should return 'Not available' when no data, not 'Contact for estimate'."""
    from worker.gamma_slideshow import GammaSlideshowCreator
    result = GammaSlideshowCreator._estimate_it_budget({})
    assert result == "Not available"
    assert "Contact" not in result


def test_it_budget_appears_in_slideshow_markdown():
    """The slideshow markdown should contain the IT budget estimate, not placeholder."""
    from worker.gamma_slideshow import GammaSlideshowCreator

    company_data = {
        "company_name": "Acme Corp",
        "validated_data": {
            "company_name": "Acme Corp",
            "industry": "Technology",
            "employee_count": 1000,
            "stakeholder_map": {"stakeholders": [], "otherContacts": []},
        },
        "confidence_score": 0.85,
    }

    creator = GammaSlideshowCreator(gamma_api_key="test_key")
    md = creator._generate_markdown(company_data)

    assert "Estimated" in md and "IT Budget" in md
    # Should have a dollar estimate, not placeholder
    assert "Contact for estimate" not in md
    assert "Contact HP RAD" not in md.lower()
    # Should contain an actual dollar amount
    assert "$10.0M - $20.0M" in md or "$" in md
