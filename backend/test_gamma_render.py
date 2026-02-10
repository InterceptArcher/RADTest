#!/usr/bin/env python3
"""
Test Gamma integration on Render.
Run this via Render shell: python3 backend/test_gamma_render.py
"""
import asyncio
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def test_gamma():
    print("="*60)
    print("GAMMA INTEGRATION TEST")
    print("="*60)

    # Check 1: Environment variable
    print("\n[1] Checking GAMMA_API_KEY...")
    api_key = os.getenv("GAMMA_API_KEY")
    if not api_key:
        print("❌ GAMMA_API_KEY not set in environment")
        return False
    print(f"✓ GAMMA_API_KEY is set (length: {len(api_key)})")

    # Check 2: Import module
    print("\n[2] Importing gamma_slideshow module...")
    try:
        sys.path.insert(0, 'worker')
        from gamma_slideshow import GammaSlideshowCreator
        print("✓ Module imported successfully")
    except Exception as e:
        print(f"❌ Failed to import: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Check 3: Initialize creator
    print("\n[3] Initializing GammaSlideshowCreator...")
    try:
        creator = GammaSlideshowCreator(api_key)
        print(f"✓ Creator initialized with template: {creator.template_id}")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Check 4: Create test slideshow
    print("\n[4] Creating test slideshow...")
    test_data = {
        "company_name": "Test Company",
        "validated_data": {
            "company_name": "Test Company",
            "industry": "Technology",
            "employee_count": "100-500",
            "company_overview": "A test company for verifying Gamma integration"
        },
        "confidence_score": 0.95
    }

    try:
        print("   Calling create_slideshow()...")
        result = await creator.create_slideshow(test_data)

        print(f"\n   Success: {result.get('success')}")
        print(f"   URL: {result.get('slideshow_url')}")
        print(f"   ID: {result.get('slideshow_id')}")
        print(f"   Error: {result.get('error')}")

        if result.get('success') and result.get('slideshow_url'):
            print("\n✅ TEST PASSED - Slideshow generated successfully!")
            print(f"   URL: {result.get('slideshow_url')}")
            return True
        else:
            print(f"\n❌ TEST FAILED - No URL returned")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"\n❌ EXCEPTION during slideshow creation:")
        print(f"   {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\nRunning async test...")
    success = asyncio.run(test_gamma())

    print("\n" + "="*60)
    if success:
        print("✅ ALL TESTS PASSED")
        print("Gamma integration is working correctly!")
    else:
        print("❌ TESTS FAILED")
        print("See errors above for details")
    print("="*60)

    sys.exit(0 if success else 1)
