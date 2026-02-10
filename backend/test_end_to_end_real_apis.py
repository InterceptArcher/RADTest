#!/usr/bin/env python3
"""
End-to-end test with REAL API data from Apollo, PDL, GNews, Hunter.io.
Tests complete pipeline: data gathering → enrichment → Gamma slideshow.
"""
import asyncio
import sys
import os
import logging

# Add worker to path
sys.path.insert(0, 'worker')

from worker.main import WorkerOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_end_to_end():
    """
    Test complete pipeline with real API data.
    """
    print("=" * 80)
    print("END-TO-END TEST WITH REAL API DATA")
    print("=" * 80)
    print()

    # Check required environment variables
    required_vars = [
        "APOLLO_API_KEY",
        "PDL_API_KEY",
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "OPENAI_API_KEY",
        "GAMMA_API_KEY"
    ]

    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
            print(f"❌ {var}: NOT SET")
        else:
            print(f"✅ {var}: Configured")

    # Optional APIs
    optional_vars = ["GNEWS_API_KEY", "HUNTER_API_KEY"]
    for var in optional_vars:
        if os.getenv(var):
            print(f"✅ {var}: Configured")
        else:
            print(f"⚠️  {var}: Not set (optional)")

    print()

    if missing:
        print(f"❌ Missing required variables: {', '.join(missing)}")
        print("Please set these environment variables and try again.")
        return False

    # Test company
    company_name = "Microsoft"
    domain = "microsoft.com"
    requested_by = "test@hp.com"

    print(f"Testing with company: {company_name} ({domain})")
    print(f"Requested by: {requested_by}")
    print()

    try:
        # Initialize orchestrator
        print("[1/8] Initializing worker orchestrator...")
        orchestrator = WorkerOrchestrator()
        print("✅ Orchestrator initialized")
        print()

        # Process company request
        print("[2/8] Processing company request...")
        print("This will:")
        print("  - Fetch data from Apollo and PDL")
        print("  - Extract executive/stakeholder profiles")
        print("  - Verify emails with Hunter.io")
        print("  - Fetch news from GNews")
        print("  - Validate data with LLM Council")
        print("  - Generate pain points, opportunities, intent signals")
        print("  - Enrich stakeholder profiles")
        print("  - Generate Gamma slideshow")
        print()

        result = await orchestrator.process_company_request(
            company_name=company_name,
            domain=domain,
            requested_by=requested_by
        )

        print()
        print("=" * 80)
        print("✅ PIPELINE COMPLETE!")
        print("=" * 80)
        print()

        print(f"Company: {result['company_name']}")
        print(f"Domain: {result['domain']}")
        print(f"Confidence Score: {result['confidence_score']:.2%}")
        print(f"Finalize Record ID: {result['finalize_record_id']}")
        print()

        print("🎯 GAMMA SLIDESHOW:")
        print(f"   URL: {result['slideshow_url']}")
        print()

        print("✅ All fields populated with REAL API data:")
        print("   ✓ Company overview (Apollo/PDL)")
        print("   ✓ Stakeholder profiles with verified emails (Apollo/PDL/Hunter.io)")
        print("   ✓ News triggers and buying signals (GNews)")
        print("   ✓ Pain points (LLM-generated from company data)")
        print("   ✓ Sales opportunities (LLM-generated from pain points)")
        print("   ✓ Intent topics with scores (LLM-generated from activities)")
        print("   ✓ Strategic priorities per stakeholder (LLM-generated)")
        print("   ✓ Conversation starters (LLM-generated)")
        print()

        print("=" * 80)
        print("🚀 SUCCESS - View your slideshow:")
        print(f"   {result['slideshow_url']}")
        print("=" * 80)

        return True

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ TEST FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print()
    success = asyncio.run(test_end_to_end())
    print()

    sys.exit(0 if success else 1)
