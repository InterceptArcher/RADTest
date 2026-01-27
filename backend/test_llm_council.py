"""
Test script to verify LLM Council is operational with OpenAI API key.
"""
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_openai_connection():
    """Test OpenAI API connection."""
    try:
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ OpenAI API key not found")
            return False

        print(f"✓ OpenAI API key loaded: {api_key[:20]}...")

        # Test with a simple completion
        print("\nTesting OpenAI API connection...")
        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": "Reply with just 'OK' if you can read this."}
            ],
            max_tokens=10,
            temperature=0
        )

        result = response.choices[0].message.content
        print(f"✓ OpenAI API responded: {result}")
        return True

    except Exception as e:
        print(f"❌ OpenAI API error: {str(e)}")
        return False


async def test_llm_council():
    """Test LLM Council conflict resolution."""
    try:
        print("\nTesting LLM Council setup...")

        # Import the council
        import sys
        sys.path.insert(0, '/workspaces/RADTest/backend/worker')
        from llm_council import LLMCouncil, SourceTier

        api_key = os.getenv("OPENAI_API_KEY")

        # Initialize council with smaller size for testing
        council = LLMCouncil(
            openai_api_key=api_key,
            council_size=3,  # Smaller for faster testing
            model="gpt-4"
        )

        print("✓ LLM Council initialized successfully")

        # Test with a simple conflict scenario
        print("\nTesting conflict resolution...")
        print("Scenario: Two sources disagree on employee count")
        print("  Source A (Apollo): 10,000 employees")
        print("  Source B (PDL): 12,500 employees")

        candidate_values = [
            {
                "value": 10000,
                "source": "apollo",
                "timestamp": "2024-01-01",
                "metadata": {}
            },
            {
                "value": 12500,
                "source": "peopledatalabs",
                "timestamp": "2024-01-15",
                "metadata": {}
            }
        ]

        source_reliability = {
            "apollo": SourceTier.TIER_1,
            "peopledatalabs": SourceTier.TIER_1
        }

        print("\nResolving conflict with 3-agent council...")
        decision = await council.resolve_conflict(
            field_name="employee_count",
            field_type="numeric",
            candidate_values=candidate_values,
            source_reliability=source_reliability
        )

        print(f"\n✓ Council Decision:")
        print(f"  Winner: {decision.winner_value}")
        print(f"  Confidence: {decision.confidence_score:.2f}")
        print(f"  Rules Applied: {', '.join(decision.rules_applied)}")
        print(f"  Council Signals: {len(decision.council_signals)} agents provided input")

        if decision.alternatives:
            print(f"\n  Alternatives:")
            for alt_value, alt_score in decision.alternatives[:2]:
                print(f"    - {alt_value} (score: {alt_score:.2f})")

        return True

    except Exception as e:
        print(f"❌ LLM Council error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test execution."""
    print("=" * 60)
    print("LLM Council Operational Test")
    print("=" * 60)

    # Test OpenAI connection first
    openai_ok = await test_openai_connection()

    if not openai_ok:
        print("\n❌ OpenAI connection failed - cannot test LLM Council")
        return

    # Test LLM Council
    council_ok = await test_llm_council()

    print("\n" + "=" * 60)
    if council_ok:
        print("✅ LLM COUNCIL IS FULLY OPERATIONAL!")
        print("\nThe multi-agent system is ready to:")
        print("  - Resolve data conflicts between sources")
        print("  - Provide high-confidence validation")
        print("  - Generate complete audit trails")
        print("  - Apply intelligent resolution rules")
    else:
        print("❌ LLM Council test failed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
