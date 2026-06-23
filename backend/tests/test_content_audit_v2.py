"""
Tests for the Content Audit V2 dataset integration.

V2 replaces the original 27-row SharePoint CSV with the 54-row HP DAM dataset
extracted from `HP Canada_RAD Intelligence Desk_Content Audit_V2_Internal.xlsx`.
The real asset URLs live behind "Access here" cell hyperlinks in the xlsx and are
pulled out by `scripts/extract_content_audit.py`.

These tests assert the loader now serves the V2 data with its renamed columns
(`Type`/`Customer Journey`/`DAM Link`) mapped onto the existing internal keys
(`ebook`/`consideration`/`sp_link`) so no downstream consumer has to change.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestContentAuditV2Dataset:
    def test_loads_all_54_assets(self):
        from content_audit import load_content_audit, get_all_items
        load_content_audit(force=True)
        items = get_all_items()
        assert len(items) == 54, f"V2 dataset has 54 assets, loaded {len(items)}"

    def test_links_are_http_or_blank(self):
        """Every sp_link is a real URL or blank — never the 'Access here' label."""
        from content_audit import load_content_audit, get_all_items
        load_content_audit(force=True)
        for it in get_all_items():
            link = it["sp_link"]
            assert link == "" or link.startswith("http"), \
                f"sp_link must be http(s) or blank, got {link!r} for {it['asset_name']!r}"
            assert "access here" not in link.lower()

    def test_49_assets_have_resolved_urls(self):
        from content_audit import load_content_audit, get_all_items
        load_content_audit(force=True)
        with_url = [it for it in get_all_items() if it["sp_link"].startswith("http")]
        assert len(with_url) == 49, f"49 assets carry a DAM hyperlink, found {len(with_url)}"

    def test_uses_public_hp_dam_domains_not_sharepoint(self):
        from content_audit import load_content_audit, get_all_items
        load_content_audit(force=True)
        links = [it["sp_link"] for it in get_all_items() if it["sp_link"].startswith("http")]
        assert any("hp.com" in l for l in links), "expected public HP DAM links"
        assert not any("sharepoint.com" in l for l in links), "V2 must not retain v1 SharePoint links"

    def test_renamed_columns_mapped_onto_internal_keys(self):
        """Type->ebook, Customer Journey->consideration, DAM Link->sp_link."""
        from content_audit import load_content_audit, get_all_items
        load_content_audit(force=True)
        items = get_all_items()
        row = next(i for i in items if i["asset_name"].startswith("High-performance power from anywhere"))
        assert row["ebook"] == "Guide"            # from V2 "Type"
        assert row["consideration"] == "Consideration"  # from V2 "Customer Journey"
        assert row["inventory_recommendations"] == "Leverage"
        assert row["format"] == "Product"
        assert row["year_published"] == "2025"
        assert row["sp_link"].startswith("http")  # from V2 "DAM Link" hyperlink

    def test_unresolved_link_rows_kept_with_blank_link(self):
        """The 5 'N/A'/'Not provided' rows still load as assets, just without a link."""
        from content_audit import load_content_audit, get_all_items
        load_content_audit(force=True)
        blank = [it for it in get_all_items() if it["sp_link"] == ""]
        assert len(blank) == 5, f"expected 5 link-less assets, found {len(blank)}"
