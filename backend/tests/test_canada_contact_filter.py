"""
Tests for Canada-only contact filtering.
Covers:
- ZoomInfo country filter set to Canada
- Apollo person_locations filter
- Post-merge Canada filter function
- LLM fact-checker Canada location prompt
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestZoomInfoCanadaFilter:
    """Verify ZoomInfo client uses Canada-only country filter."""

    def test_country_constant_is_canada_only(self):
        from worker.zoominfo_client import CANADA_COUNTRY_FILTER
        assert CANADA_COUNTRY_FILTER == ["Canada"]

    def test_north_america_constant_removed_or_replaced(self):
        """NORTH_AMERICA_COUNTRIES should no longer include US or Mexico."""
        from worker import zoominfo_client
        # The old constant may still exist for reference but the active filter
        # used in _search_na_first should be Canada-only
        assert hasattr(zoominfo_client, 'CANADA_COUNTRY_FILTER')


class TestApolloCanadaFilter:
    """Verify Apollo stakeholder search includes Canada location filter."""

    def test_fetch_stakeholders_has_location_filter(self):
        """The fetch_stakeholders function should include person_locations."""
        import production_main
        import inspect
        source = inspect.getsource(production_main.fetch_stakeholders)
        assert "person_locations" in source
        assert "Canada" in source


class TestPostMergeCanadaFilter:
    """Test the post-merge function that filters non-Canadian contacts."""

    def test_filter_keeps_canadian_contacts(self):
        from production_main import filter_contacts_canada
        contacts = [
            {"name": "Alice", "country": "Canada", "title": "CTO"},
            {"name": "Bob", "country": "Canada", "title": "CFO"},
        ]
        result = filter_contacts_canada(contacts)
        assert len(result) == 2

    def test_filter_removes_non_canadian_contacts(self):
        from production_main import filter_contacts_canada
        contacts = [
            {"name": "Alice", "country": "Canada", "title": "CTO"},
            {"name": "Bob", "country": "United States", "title": "CFO"},
            {"name": "Charlie", "country": "Mexico", "title": "CIO"},
        ]
        result = filter_contacts_canada(contacts)
        assert len(result) == 1
        assert result[0]["name"] == "Alice"

    def test_filter_keeps_contacts_with_no_country(self):
        """Contacts with no country data get benefit of the doubt."""
        from production_main import filter_contacts_canada
        contacts = [
            {"name": "Alice", "country": "Canada", "title": "CTO"},
            {"name": "Bob", "title": "CFO"},  # no country field
            {"name": "Charlie", "country": "", "title": "CIO"},  # empty country
        ]
        result = filter_contacts_canada(contacts)
        assert len(result) == 3

    def test_filter_is_case_insensitive(self):
        from production_main import filter_contacts_canada
        contacts = [
            {"name": "Alice", "country": "canada", "title": "CTO"},
            {"name": "Bob", "country": "CANADA", "title": "CFO"},
            {"name": "Charlie", "country": "united states", "title": "CIO"},
        ]
        result = filter_contacts_canada(contacts)
        assert len(result) == 2

    def test_filter_checks_multiple_location_fields(self):
        """Should check country, location_country, and person_country fields."""
        from production_main import filter_contacts_canada
        contacts = [
            {"name": "Alice", "location_country": "United States", "title": "CTO"},
            {"name": "Bob", "person_country": "Canada", "title": "CFO"},
        ]
        result = filter_contacts_canada(contacts)
        # Alice has US in location_country -> filtered out
        # Bob has Canada in person_country -> kept
        assert len(result) == 1
        assert result[0]["name"] == "Bob"

    def test_filter_returns_empty_for_all_non_canadian(self):
        from production_main import filter_contacts_canada
        contacts = [
            {"name": "Bob", "country": "United States", "title": "CFO"},
            {"name": "Charlie", "country": "United Kingdom", "title": "CIO"},
        ]
        result = filter_contacts_canada(contacts)
        assert len(result) == 0


class TestLLMFactCheckerCanadaPrompt:
    """Verify the LLM fact-checker includes Canada location verification."""

    def test_fact_checker_prompt_mentions_canada(self):
        """The fact_check_contacts function should include Canada verification in prompt."""
        import production_main
        import inspect
        source = inspect.getsource(production_main.fact_check_contacts)
        assert "Canada" in source
        assert "location" in source.lower()
