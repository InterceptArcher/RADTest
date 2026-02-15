#!/usr/bin/env python3
"""
Test script to validate the gamma URL extraction fix.
This simulates different API response scenarios.
"""
import sys


def extract_gamma_url(status_data, generation_id):
    """
    Extract URL from Gamma API response using the same logic as the fixed code.

    Args:
        status_data: The status response from Gamma API
        generation_id: The generation ID

    Returns:
        str: The extracted or constructed URL
    """
    # Try multiple possible URL keys
    gamma_url = (
        status_data.get("gammaUrl") or
        status_data.get("url") or
        status_data.get("webUrl") or
        status_data.get("gamma_url")
    )

    # Fallback: Search all keys for any URL-like field
    if not gamma_url:
        print("  → Standard URL fields not found, searching all fields...")
        for key, value in status_data.items():
            if isinstance(value, str) and ("gamma.app" in value or "http" in value):
                print(f"  → Found URL-like value in field '{key}': {value}")
                gamma_url = value
                break

    # Check nested objects for URL
    if not gamma_url and isinstance(status_data.get("gamma"), dict):
        print("  → Checking nested 'gamma' object...")
        gamma_url = status_data["gamma"].get("url") or status_data["gamma"].get("webUrl")

    # Check if URL is in a 'data' wrapper
    if not gamma_url and isinstance(status_data.get("data"), dict):
        print("  → Checking nested 'data' object...")
        gamma_url = status_data["data"].get("url") or status_data["data"].get("gammaUrl")

    # Check for 'link' or 'viewLink' fields
    if not gamma_url:
        print("  → Checking link fields...")
        gamma_url = status_data.get("link") or status_data.get("viewLink") or status_data.get("shareLink")

    # CRITICAL FIX: Construct valid URL from generation ID if still not found
    if not gamma_url and generation_id:
        print(f"  → Constructing URL from generation ID: {generation_id}")
        gamma_url = f"https://gamma.app/docs/{generation_id}"

    return gamma_url


def test_scenario(name, status_data, generation_id, expected_url):
    """Test a specific scenario"""
    print(f"\nTest: {name}")
    print(f"  Status data keys: {list(status_data.keys())}")
    print(f"  Generation ID: {generation_id}")

    result = extract_gamma_url(status_data, generation_id)

    if result:
        print(f"  ✅ Result: {result}")
        if expected_url and result != expected_url:
            print(f"  ⚠️  Expected: {expected_url}")
            return False
        return True
    else:
        print(f"  ❌ No URL extracted!")
        return False


def main():
    """Run all test scenarios"""
    print("=" * 80)
    print("GAMMA URL EXTRACTION TEST")
    print("=" * 80)

    tests_passed = 0
    tests_total = 0

    # Scenario 1: URL in gammaUrl field
    tests_total += 1
    if test_scenario(
        "URL in gammaUrl field",
        {"status": "completed", "gammaUrl": "https://gamma.app/docs/abc123"},
        "abc123",
        "https://gamma.app/docs/abc123"
    ):
        tests_passed += 1

    # Scenario 2: URL in url field
    tests_total += 1
    if test_scenario(
        "URL in url field",
        {"status": "completed", "url": "https://gamma.app/docs/def456"},
        "def456",
        "https://gamma.app/docs/def456"
    ):
        tests_passed += 1

    # Scenario 3: URL in nested gamma object
    tests_total += 1
    if test_scenario(
        "URL in nested gamma object",
        {"status": "completed", "gamma": {"url": "https://gamma.app/docs/ghi789"}},
        "ghi789",
        "https://gamma.app/docs/ghi789"
    ):
        tests_passed += 1

    # Scenario 4: No URL field, must construct from generation ID
    tests_total += 1
    if test_scenario(
        "No URL field (construct from generation ID)",
        {"status": "completed", "generationId": "xyz999"},
        "xyz999",
        "https://gamma.app/docs/xyz999"
    ):
        tests_passed += 1

    # Scenario 5: URL with different domain (gamma.to)
    tests_total += 1
    if test_scenario(
        "URL with different domain (gamma.to)",
        {"status": "completed", "link": "https://gamma.to/short-url"},
        "abc111",
        "https://gamma.to/short-url"
    ):
        tests_passed += 1

    # Scenario 6: URL in webUrl field
    tests_total += 1
    if test_scenario(
        "URL in webUrl field",
        {"status": "completed", "webUrl": "https://gamma.app/docs/web222"},
        "web222",
        "https://gamma.app/docs/web222"
    ):
        tests_passed += 1

    print("\n" + "=" * 80)
    print(f"RESULTS: {tests_passed}/{tests_total} tests passed")
    print("=" * 80)

    return 0 if tests_passed == tests_total else 1


if __name__ == "__main__":
    sys.exit(main())
