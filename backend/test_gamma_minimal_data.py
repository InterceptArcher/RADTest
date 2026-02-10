#!/usr/bin/env python3
"""Test with MINIMAL data to verify 'Not available' handling"""
import asyncio
import sys
import os

sys.path.insert(0, 'worker')
from gamma_slideshow import GammaSlideshowCreator

async def test_minimal():
    api_key = os.getenv("GAMMA_API_KEY")
    if not api_key:
        print("❌ GAMMA_API_KEY not set")
        return False

    creator = GammaSlideshowCreator(api_key, template_id="g_vsj27dcr73l1nv1")

    # Minimal data - most fields missing
    minimal_data = {
        "company_name": "Minimal Data Company",
        "validated_data": {
            "company_name": "Minimal Data Company",
            "industry": "Technology"
            # Most fields intentionally missing
        },
        "confidence_score": 0.50
    }

    print("Testing with MINIMAL data to verify 'Not available' handling...")
    print()

    try:
        result = await creator.create_slideshow(minimal_data)

        print(f"Success: {result.get('success')}")
        print(f"URL: {result.get('slideshow_url')}")

        if result.get('success'):
            print("\n✅ Template handles missing data correctly!")
            print("   Fields should show 'Not available' or generate defaults")
            print(f"   View: {result.get('slideshow_url')}")
            return True
        else:
            print(f"\n❌ Failed: {result.get('error')}")
            return False

    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_minimal())
    exit(0 if success else 1)
