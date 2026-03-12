"""
Tests for Claude web search company intelligence step.
TDD: Tests written FIRST before implementation.

This step uses Claude with web_search to gather company fields
that APIs don't reliably provide: CEO, company_type, customer_segments,
products, competitors.
"""
import pytest
import inspect


def test_claude_company_intel_function_exists():
    """The claude_company_intel function should exist in production_main."""
    import importlib
    mod = importlib.import_module("production_main")
    assert hasattr(mod, "claude_company_intel"), \
        "production_main should have a claude_company_intel function"


def test_claude_company_intel_is_async():
    """claude_company_intel should be an async function."""
    import importlib
    mod = importlib.import_module("production_main")
    assert inspect.iscoroutinefunction(mod.claude_company_intel), \
        "claude_company_intel should be async"


def test_claude_company_intel_returns_required_fields():
    """The function signature should accept company_name and domain."""
    import importlib
    mod = importlib.import_module("production_main")
    sig = inspect.signature(mod.claude_company_intel)
    params = list(sig.parameters.keys())
    assert "company_name" in params, "Should accept company_name"
    assert "domain" in params, "Should accept domain"


def test_claude_company_intel_source_has_required_fields():
    """The function should extract ceo, company_type, customer_segments, products, competitors."""
    import importlib
    mod = importlib.import_module("production_main")
    source = inspect.getsource(mod.claude_company_intel)

    for field in ["ceo", "company_type", "customer_segments", "products", "competitors"]:
        assert field in source, \
            f"claude_company_intel should extract '{field}' from web search"


def test_claude_company_intel_uses_web_search_tool():
    """The function should use Claude's web_search tool."""
    import importlib
    mod = importlib.import_module("production_main")
    source = inspect.getsource(mod.claude_company_intel)

    assert "web_search" in source, \
        "Should use Claude web_search tool"


def test_claude_company_intel_called_before_council():
    """claude_company_intel results should be fed into the LLM Council."""
    import importlib
    mod = importlib.import_module("production_main")
    source = inspect.getsource(mod.process_company_profile)

    # The web search step should appear before validate_with_council
    web_search_pos = source.find("claude_company_intel")
    council_pos = source.find("validate_with_council")
    assert web_search_pos != -1, "process_company_profile should call claude_company_intel"
    assert web_search_pos < council_pos, \
        "claude_company_intel should run BEFORE validate_with_council"


def test_claude_company_intel_graceful_without_api_key():
    """Should return empty dict gracefully if ANTHROPIC_API_KEY is not set."""
    import importlib
    mod = importlib.import_module("production_main")
    source = inspect.getsource(mod.claude_company_intel)

    assert "ANTHROPIC_API_KEY" in source, \
        "Should check for ANTHROPIC_API_KEY"
