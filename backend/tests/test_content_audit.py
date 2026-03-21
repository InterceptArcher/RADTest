"""
Tests for the content audit module.
Covers CSV loading, keyword matching for gamma integration, and user-added items.
"""
import os
import sys
import pytest

# Ensure backend is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestContentAuditLoading:
    """Test that the CSV loads correctly and items are accessible."""

    def test_load_csv_returns_items(self):
        from content_audit import load_content_audit, get_all_items
        load_content_audit()
        items = get_all_items()
        assert len(items) > 0, "Should load at least one item from CSV"

    def test_items_have_required_fields(self):
        from content_audit import load_content_audit, get_all_items
        load_content_audit()
        items = get_all_items()
        for item in items:
            assert 'asset_name' in item
            assert 'sp_link' in item
            assert 'asset_summary' in item

    def test_items_have_metadata_fields(self):
        from content_audit import load_content_audit, get_all_items
        load_content_audit()
        items = get_all_items()
        first = items[0]
        assert 'industry' in first
        assert 'service_solution' in first
        assert 'year_published' in first
        assert 'audience' in first
        assert 'format' in first


class TestContentAuditMatching:
    """Test the matching logic that selects content audit items for gamma output."""

    def test_match_by_keyword_returns_result(self):
        from content_audit import load_content_audit, match_content
        load_content_audit()
        result = match_content(keywords=["AI workstation"])
        assert result is not None
        assert 'asset_name' in result

    def test_match_by_industry(self):
        from content_audit import load_content_audit, match_content
        load_content_audit()
        result = match_content(keywords=["fleet management"], audience="ITDM")
        assert result is not None

    def test_match_returns_none_for_nonsense(self):
        from content_audit import load_content_audit, match_content
        load_content_audit()
        result = match_content(keywords=["zzz_nonexistent_xyz_gibberish"])
        # Should still return something (best available) or None
        # The function should gracefully handle no matches
        # It should return a fallback item rather than crashing
        assert result is None or 'asset_name' in result

    def test_match_prefers_leverage_over_retire(self):
        from content_audit import load_content_audit, match_content
        load_content_audit()
        result = match_content(keywords=["workforce", "hybrid work"])
        if result:
            assert result.get('inventory_recommendations') != 'Retire', \
                "Should prefer Leverage/Upcycle items over Retire"

    def test_match_for_collateral_step(self):
        """Match content for the marketing collateral field in recommended sales program."""
        from content_audit import load_content_audit, match_content_for_collateral
        load_content_audit()
        result = match_content_for_collateral(
            step_description="Build awareness and credibility",
            industry="technology",
            intent_topic="AI modernization"
        )
        assert result is not None
        assert 'asset_name' in result
        assert 'sp_link' in result

    def test_match_for_supporting_asset(self):
        """Match content for the [Insert link to supporting asset] placeholder."""
        from content_audit import load_content_audit, match_content_for_supporting_asset
        load_content_audit()
        result = match_content_for_supporting_asset(
            persona="CTO",
            industry="technology",
            priority_area="AI workstations"
        )
        assert result is not None
        assert 'asset_name' in result
        assert 'sp_link' in result


class TestContentAuditUserItems:
    """Test adding user-defined content audit items."""

    def test_add_user_item(self):
        from content_audit import load_content_audit, add_item, get_all_items
        load_content_audit()
        initial_count = len(get_all_items())
        add_item(
            asset_name="Custom Resource",
            sp_link="https://example.com/resource",
            asset_summary="A custom resource for testing",
        )
        assert len(get_all_items()) == initial_count + 1

    def test_user_item_appears_in_list(self):
        from content_audit import load_content_audit, add_item, get_all_items
        load_content_audit()
        add_item(
            asset_name="My Test Asset",
            sp_link="https://example.com/test",
            asset_summary="Test summary",
        )
        items = get_all_items()
        names = [i['asset_name'] for i in items]
        assert "My Test Asset" in names
