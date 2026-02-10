#!/usr/bin/env python3
"""
Test the /test-slideshow endpoint on Render to verify Gamma integration.
"""
import requests
import json
import sys

# Render URL - update this with your actual Render service URL
RENDER_URL = "https://radtest-backend.onrender.com"  # Update if different
TEST_ENDPOINT = f"{RENDER_URL}/test-slideshow"

def test_slideshow(company_name="Airbnb"):
    """
    Test slideshow generation for a given company.
    """
    print("=" * 80)
    print(f"TESTING SLIDESHOW GENERATION FOR: {company_name}")
    print("=" * 80)
    print()

    print(f"🌐 Calling endpoint: {TEST_ENDPOINT}")
    print(f"📊 Company: {company_name}")
    print()

    try:
        # Call the test endpoint
        response = requests.post(
            TEST_ENDPOINT,
            params={"company_name": company_name},
            timeout=300  # 5 minute timeout for slideshow generation
        )

        response.raise_for_status()
        result = response.json()

        print("=" * 80)
        print("RESPONSE:")
        print("=" * 80)
        print(json.dumps(result, indent=2))
        print()

        # Check result
        if result.get("test") == "PASSED ✅":
            print("✅ TEST PASSED!")
            print(f"   Slideshow URL: {result.get('slideshow_url')}")
            print(f"   Slideshow ID: {result.get('slideshow_id')}")
            return True
        else:
            print("❌ TEST FAILED!")
            print(f"   Error: {result.get('error')}")
            print(f"   Message: {result.get('message')}")
            return False

    except requests.exceptions.Timeout:
        print("❌ REQUEST TIMED OUT")
        print("   Slideshow generation took longer than 5 minutes")
        return False

    except requests.exceptions.RequestException as e:
        print(f"❌ REQUEST FAILED: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Status Code: {e.response.status_code}")
            print(f"   Response: {e.response.text}")
        return False

    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    company = sys.argv[1] if len(sys.argv) > 1 else "Airbnb"

    print(f"\n🧪 Testing Gamma slideshow generation...")
    print(f"   Company: {company}")
    print(f"   Endpoint: {TEST_ENDPOINT}")
    print()

    success = test_slideshow(company)

    print()
    print("=" * 80)
    if success:
        print("✅ GAMMA INTEGRATION WORKING")
    else:
        print("❌ GAMMA INTEGRATION BROKEN - Check logs above")
    print("=" * 80)
    print()

    sys.exit(0 if success else 1)
