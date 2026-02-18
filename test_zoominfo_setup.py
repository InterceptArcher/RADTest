"""
Test script to verify ZoomInfo credentials are configured correctly.
Run this to test contact enrichment functionality.
"""
import os
import asyncio
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
sys.path.insert(0, 'backend/worker')

from zoominfo_client import ZoomInfoClient

async def test_zoominfo():
    """Test ZoomInfo authentication and contact enrichment."""

    print("=" * 60)
    print("ZOOMINFO CREDENTIALS TEST")
    print("=" * 60)

    # Check environment variables
    client_id = os.getenv("ZOOMINFO_CLIENT_ID")
    client_secret = os.getenv("ZOOMINFO_CLIENT_SECRET")
    access_token = os.getenv("ZOOMINFO_ACCESS_TOKEN")

    print("\n1. Environment Variables:")
    print(f"   ZOOMINFO_CLIENT_ID: {'✓ SET' if client_id else '✗ MISSING'}")
    print(f"   ZOOMINFO_CLIENT_SECRET: {'✓ SET' if client_secret else '✗ MISSING'}")
    print(f"   ZOOMINFO_ACCESS_TOKEN: {'✓ SET' if access_token else '✗ MISSING'}")

    if not (client_id and client_secret) and not access_token:
        print("\n❌ ERROR: No ZoomInfo credentials found!")
        print("   Please set either:")
        print("   - ZOOMINFO_CLIENT_ID + ZOOMINFO_CLIENT_SECRET (recommended)")
        print("   - ZOOMINFO_ACCESS_TOKEN")
        return False

    # Create client
    print("\n2. Creating ZoomInfo Client...")
    try:
        if client_id and client_secret:
            client = ZoomInfoClient(
                client_id=client_id,
                client_secret=client_secret
            )
            print("   ✓ Client created with OAuth credentials")
        else:
            client = ZoomInfoClient(access_token=access_token)
            print("   ✓ Client created with access token")
    except Exception as e:
        print(f"   ✗ Failed to create client: {e}")
        return False

    # Test authentication
    print("\n3. Testing Authentication...")
    try:
        await client._ensure_valid_token()
        print("   ✓ Authentication successful")
        print(f"   Token: {client.access_token[:20]}...")
    except Exception as e:
        print(f"   ✗ Authentication failed: {e}")
        return False

    # Test contact search (using a known company domain)
    print("\n4. Testing Contact Search & Enrichment...")
    test_domain = "hp.com"
    print(f"   Testing with domain: {test_domain}")

    try:
        result = await client.search_and_enrich_contacts(
            domain=test_domain,
            max_results=5
        )

        if result.get("success"):
            people = result.get("people", [])
            print(f"   ✓ Contact enrichment successful!")
            print(f"   Found {len(people)} contacts")

            if people:
                print("\n   Sample contact data:")
                contact = people[0]
                print(f"   - Name: {contact.get('name', 'N/A')}")
                print(f"   - Title: {contact.get('title', 'N/A')}")
                print(f"   - Email: {contact.get('email', 'N/A')}")
                print(f"   - Direct Phone: {contact.get('direct_phone', 'N/A')}")
                print(f"   - Mobile Phone: {contact.get('mobile_phone', 'N/A')}")
                print(f"   - Management Level: {contact.get('management_level', 'N/A')}")
                print(f"   - Department: {contact.get('department', 'N/A')}")
                print(f"   - Accuracy Score: {contact.get('contact_accuracy_score', 'N/A')}")
        else:
            error = result.get("error", "Unknown error")
            print(f"   ✗ Contact enrichment failed: {error}")
            return False

    except Exception as e:
        print(f"   ✗ Contact search failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED - ZoomInfo is configured correctly!")
    print("=" * 60)
    print("\nContact enrichment is ready to use in your application.")
    print("The system will automatically enrich contacts when you create")
    print("a company profile request.")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_zoominfo())
    sys.exit(0 if success else 1)
