#!/usr/bin/env python3
"""
Test script for Gamma API integration.
Tests slideshow generation with sample company data.
"""
import asyncio
import os
import sys
import logging
from dotenv import load_dotenv

# Configure verbose logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Load environment variables
load_dotenv()

# Add worker directory to path
sys.path.insert(0, 'worker')

from gamma_slideshow import GammaSlideshowCreator


async def test_gamma_slideshow():
    """Test Gamma slideshow generation with sample data."""

    gamma_api_key = os.getenv("GAMMA_API_KEY")

    if not gamma_api_key:
        print("ERROR: GAMMA_API_KEY not found in environment")
        return False

    print(f"✓ Gamma API key loaded: {gamma_api_key[:15]}...")

    # Sample company data
    company_data = {
        "company_name": "Acme Corporation",
        "validated_data": {
            "company_name": "Acme Corporation",
            "domain": "acme.com",
            "industry": "Technology",
            "headquarters": "San Francisco, CA",
            "employee_count": "1,000-5,000",
            "revenue": "$100M - $500M",
            "founded_year": "2015",
            "ceo": "Jane Smith",
            "target_market": "B2B Enterprise",
            "technology": ["Python", "React", "AWS", "PostgreSQL"],
            "contacts": {
                "website": "acme.com",
                "linkedin": "https://linkedin.com/company/acme",
                "email": "info@acme.com"
            }
        },
        "confidence_score": 0.92
    }

    print("\n📝 Creating slideshow for:", company_data["company_name"])

    try:
        creator = GammaSlideshowCreator(gamma_api_key)
        print("✓ GammaSlideshowCreator initialized")

        result = await creator.create_slideshow(company_data)

        if result.get("success"):
            print("\n✅ SUCCESS!")
            print(f"   Slideshow URL: {result.get('slideshow_url')}")
            print(f"   Slideshow ID: {result.get('slideshow_id')}")
            return True
        else:
            print("\n❌ FAILED!")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"\n❌ EXCEPTION: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Gamma API Integration Test")
    print("=" * 60)

    success = asyncio.run(test_gamma_slideshow())

    print("\n" + "=" * 60)
    if success:
        print("✅ Test PASSED - Gamma integration is working!")
    else:
        print("❌ Test FAILED - Check errors above")
    print("=" * 60)

    sys.exit(0 if success else 1)
