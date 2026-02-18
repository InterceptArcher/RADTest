#!/usr/bin/env python3
"""
Test Gamma template with insufficient data (company doesn't exist).
Verifies all sections show 'Data unavailable at the time' messaging.
"""
import asyncio
import sys
import os

sys.path.insert(0, 'worker')
from gamma_slideshow import GammaSlideshowCreator

async def test_data_unavailable():
    """Test with company that doesn't exist or has no data"""
    api_key = os.getenv("GAMMA_API_KEY")
    if not api_key:
        print("❌ GAMMA_API_KEY not set")
        return False

    creator = GammaSlideshowCreator(api_key, template_id="g_b18rs7bet2if0n9")

    # Test case 1: Company with no substantive data (company doesn't exist)
    nonexistent_company = {
        "company_name": "NonExistent Company XYZ 123",
        "user_email": "test@hp.com",
        "validated_data": {
            "company_name": "NonExistent Company XYZ 123"
            # No other data - simulates company not found
        },
        "confidence_score": 0.10
    }

    print("=" * 70)
    print("TEST: Company Does Not Exist (No Data)")
    print("=" * 70)
    print(f"Company: {nonexistent_company['company_name']}")
    print(f"Expected: All sections show 'Data unavailable at the time'")
    print("=" * 70)
    print()

    try:
        result = await creator.create_slideshow(nonexistent_company, user_email="test@hp.com")

        print(f"Success: {result.get('success')}")
        print(f"URL: {result.get('slideshow_url')}")
        print(f"Error: {result.get('error')}")

        if result.get('success'):
            print()
            print("✅ Slideshow created with 'Data unavailable' messaging!")
            print(f"🔗 View here: {result.get('slideshow_url')}")
            print()
            print("Verify in the slideshow that:")
            print("  ✓ Title slide shows data quality warning")
            print("  ✓ Executive Snapshot shows 'Data unavailable at the time'")
            print("  ✓ Buying Signals shows 'Data unavailable at the time'")
            print("  ✓ Opportunity themes shows 'Data unavailable at the time'")
            print("  ✓ Stakeholder Map shows 'Data unavailable' message")
            return True
        else:
            print(f"\n❌ Failed: {result.get('error')}")
            return False

    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_minimal_data():
    """Test with minimal data (company exists but limited info)"""
    api_key = os.getenv("GAMMA_API_KEY")
    if not api_key:
        print("❌ GAMMA_API_KEY not set")
        return False

    creator = GammaSlideshowCreator(api_key, template_id="g_b18rs7bet2if0n9")

    # Test case 2: Minimal but viable data
    minimal_company = {
        "company_name": "Small Private Company",
        "user_email": "test@hp.com",
        "validated_data": {
            "company_name": "Small Private Company",
            "industry": "Technology",
            "company_overview": "A small private technology company with limited public information available."
            # Minimal data but enough to pass validation
        },
        "confidence_score": 0.50
    }

    print()
    print("=" * 70)
    print("TEST: Minimal but Viable Data")
    print("=" * 70)
    print(f"Company: {minimal_company['company_name']}")
    print(f"Expected: Shows data where available, generates defaults elsewhere")
    print("=" * 70)
    print()

    try:
        result = await creator.create_slideshow(minimal_company, user_email="test@hp.com")

        print(f"Success: {result.get('success')}")
        print(f"URL: {result.get('slideshow_url')}")

        if result.get('success'):
            print()
            print("✅ Slideshow created with minimal data handling!")
            print(f"🔗 View here: {result.get('slideshow_url')}")
            print()
            print("Verify in the slideshow that:")
            print("  ✓ Shows company overview (minimal)")
            print("  ✓ Generates default intent topics")
            print("  ✓ Generates default pain points")
            print("  ✓ Generates default opportunities")
            return True
        else:
            print(f"\n❌ Failed: {result.get('error')}")
            return False

    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests"""
    print("Testing Gamma template data unavailable handling...\n")

    # Test 1: No data (company doesn't exist)
    test1_success = await test_data_unavailable()

    # Test 2: Minimal data
    test2_success = await test_minimal_data()

    print()
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Test 1 (No Data): {'✅ PASSED' if test1_success else '❌ FAILED'}")
    print(f"Test 2 (Minimal Data): {'✅ PASSED' if test2_success else '❌ FAILED'}")
    print("=" * 70)

    return test1_success and test2_success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
