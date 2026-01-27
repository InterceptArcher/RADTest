"""
Quick test to verify Apollo API key is working.
"""
import asyncio
import os
from dotenv import load_dotenv
import httpx

# Load environment variables
load_dotenv()

async def test_apollo_key():
    """Test Apollo API key with a simple request."""
    api_key = os.getenv("APOLLO_API_KEY")

    if not api_key:
        print("❌ Apollo API key not found in environment")
        return False

    print(f"✓ Apollo API key loaded: {api_key[:10]}...")

    # Test the API key with a simple organization search
    try:
        async with httpx.AsyncClient() as client:
            print("\nTesting Apollo API key with a search request...")
            response = await client.post(
                "https://api.apollo.io/v1/organizations/search",
                headers={"X-Api-Key": api_key},
                json={
                    "q_organization_name": "Microsoft",
                    "page": 1,
                    "per_page": 1
                },
                timeout=30.0
            )

            print(f"Response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✓ Apollo API key is working!")
                print(f"✓ Found {len(data.get('organizations', []))} organization(s)")
                if data.get('organizations'):
                    org = data['organizations'][0]
                    print(f"✓ Sample result: {org.get('name', 'N/A')}")
                return True
            elif response.status_code == 401:
                print("❌ Apollo API key is invalid (401 Unauthorized)")
                return False
            elif response.status_code == 429:
                print("⚠️  Rate limit reached")
                return True  # Key is valid, just rate limited
            else:
                print(f"⚠️  Unexpected response: {response.status_code}")
                print(f"Response: {response.text[:200]}")
                return False

    except Exception as e:
        print(f"❌ Error testing Apollo API: {e}")
        return False

async def main():
    print("=" * 60)
    print("Apollo API Key Test")
    print("=" * 60)

    success = await test_apollo_key()

    print("\n" + "=" * 60)
    if success:
        print("✓ Apollo API key is configured and working!")
        print("✓ LLM Council can now use Apollo for intelligence gathering")
    else:
        print("❌ Apollo API key test failed")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
