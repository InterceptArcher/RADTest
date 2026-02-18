#!/usr/bin/env python3
"""
Diagnostic test to identify why gamma URL is null.
Tests the full worker pipeline with detailed logging.
"""
import asyncio
import sys
import os
import json
import logging

# Add worker to path
sys.path.insert(0, 'worker')

from worker.gamma_slideshow import GammaSlideshowCreator

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_gamma_with_email():
    """
    Test Gamma slideshow with user_email parameter.
    """
    print("=" * 80)
    print("GAMMA DIAGNOSTIC TEST - WITH USER EMAIL")
    print("=" * 80)
    print()

    # Check API key
    api_key = os.getenv("GAMMA_API_KEY")
    if not api_key:
        print("❌ GAMMA_API_KEY not set")
        return False

    print(f"✅ GAMMA_API_KEY: {api_key[:20]}...")
    print()

    # Test data
    test_company_data = {
        "company_name": "Test Company",
        "validated_data": {
            "company_name": "Test Company",
            "domain": "testcompany.com",
            "industry": "Technology",
            "employee_count": "500-1000",
            "company_overview": "A technology company focused on innovation",
            "intent_topics": [
                {"topic": "Cloud Migration", "score": 85},
                {"topic": "Cybersecurity", "score": 78}
            ],
            "pain_points": [
                {
                    "title": "Legacy Infrastructure",
                    "description": "Outdated systems limiting scalability"
                }
            ],
            "sales_opportunities": [
                {
                    "title": "Cloud Infrastructure Assessment",
                    "description": "Evaluate current state and migration path"
                }
            ],
            "stakeholder_profiles": [
                {
                    "name": "John Doe",
                    "title": "CTO",
                    "email": "john.doe@testcompany.com",
                    "phone": "+1-555-0100",
                    "linkedin": "https://linkedin.com/in/johndoe"
                }
            ]
        },
        "confidence_score": 0.92
    }

    test_user_email = "test@hp.com"

    print(f"Company: {test_company_data['company_name']}")
    print(f"User Email: {test_user_email}")
    print()

    try:
        # Initialize creator with template
        print("[1] Initializing GammaSlideshowCreator...")
        creator = GammaSlideshowCreator(
            gamma_api_key=api_key,
            template_id="g_b18rs7bet2if0n9"
        )
        print(f"✅ Creator initialized with template: {creator.template_id}")
        print()

        # Create slideshow WITH user_email
        print("[2] Creating slideshow WITH user_email parameter...")
        print(f"    Calling: create_slideshow(company_data, user_email='{test_user_email}')")
        print()

        result = await creator.create_slideshow(
            company_data=test_company_data,
            user_email=test_user_email
        )

        print()
        print("=" * 80)
        print("RESULT:")
        print("=" * 80)
        print(json.dumps(result, indent=2))
        print()

        # Check result
        if result.get("success") and result.get("slideshow_url"):
            print("✅ SUCCESS!")
            print(f"   Slideshow URL: {result['slideshow_url']}")
            return True
        else:
            print("❌ FAILED - No URL returned")
            print(f"   Error: {result.get('error', 'Unknown')}")
            return False

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ EXCEPTION:")
        print("=" * 80)
        print(f"{e}")
        print()
        import traceback
        traceback.print_exc()
        return False


async def test_gamma_without_email():
    """
    Test Gamma slideshow WITHOUT user_email parameter.
    """
    print()
    print("=" * 80)
    print("GAMMA DIAGNOSTIC TEST - WITHOUT USER EMAIL")
    print("=" * 80)
    print()

    # Check API key
    api_key = os.getenv("GAMMA_API_KEY")
    if not api_key:
        print("❌ GAMMA_API_KEY not set")
        return False

    print(f"✅ GAMMA_API_KEY: {api_key[:20]}...")
    print()

    # Test data
    test_company_data = {
        "company_name": "Test Company 2",
        "validated_data": {
            "company_name": "Test Company 2",
            "domain": "testcompany2.com",
            "industry": "Healthcare",
            "employee_count": "1000-5000"
        },
        "confidence_score": 0.88
    }

    print(f"Company: {test_company_data['company_name']}")
    print("User Email: <NOT PROVIDED>")
    print()

    try:
        # Initialize creator
        print("[1] Initializing GammaSlideshowCreator...")
        creator = GammaSlideshowCreator(
            gamma_api_key=api_key,
            template_id="g_b18rs7bet2if0n9"
        )
        print(f"✅ Creator initialized")
        print()

        # Create slideshow WITHOUT user_email
        print("[2] Creating slideshow WITHOUT user_email parameter...")
        print(f"    Calling: create_slideshow(company_data)")
        print()

        result = await creator.create_slideshow(
            company_data=test_company_data
        )

        print()
        print("=" * 80)
        print("RESULT:")
        print("=" * 80)
        print(json.dumps(result, indent=2))
        print()

        # Check result
        if result.get("success") and result.get("slideshow_url"):
            print("✅ SUCCESS!")
            print(f"   Slideshow URL: {result['slideshow_url']}")
            return True
        else:
            print("❌ FAILED - No URL returned")
            print(f"   Error: {result.get('error', 'Unknown')}")
            return False

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ EXCEPTION:")
        print("=" * 80)
        print(f"{e}")
        print()
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print()

    # Test with email
    success_with_email = asyncio.run(test_gamma_with_email())

    # Test without email
    success_without_email = asyncio.run(test_gamma_without_email())

    print()
    print("=" * 80)
    print("SUMMARY:")
    print("=" * 80)
    print(f"With user_email:    {'✅ PASS' if success_with_email else '❌ FAIL'}")
    print(f"Without user_email: {'✅ PASS' if success_without_email else '❌ FAIL'}")
    print("=" * 80)
    print()

    sys.exit(0 if (success_with_email and success_without_email) else 1)
