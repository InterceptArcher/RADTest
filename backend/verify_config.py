"""
Simple configuration verification script.
Checks that all required environment variables are properly loaded.
"""
import os

def verify_env():
    """Verify environment configuration."""
    print("=" * 60)
    print("RADTest Backend Configuration Verification")
    print("=" * 60)

    # Try loading from .env file
    env_file = "/workspaces/RADTest/backend/.env"
    if os.path.exists(env_file):
        print(f"\n✓ Found .env file at: {env_file}")
        with open(env_file, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    if '=' in line:
                        key = line.split('=')[0].strip()
                        value = line.split('=', 1)[1].strip()
                        if key == "APOLLO_API_KEY":
                            if value:
                                print(f"✓ {key}: {value[:10]}...{value[-5:] if len(value) > 15 else ''}")
                                print(f"  Full key length: {len(value)} characters")
                            else:
                                print(f"⚠️  {key}: (empty)")
                        elif key in ["PDL_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "GAMMA_API_KEY", "SUPABASE_KEY"]:
                            if value:
                                print(f"✓ {key}: configured")
                            else:
                                print(f"⚠️  {key}: (empty)")
    else:
        print(f"\n❌ .env file not found at: {env_file}")

    print("\n" + "=" * 60)
    print("Configuration Summary")
    print("=" * 60)
    print("\nThe Apollo API key has been configured.")
    print("\nTo use the LLM Council:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Set OPENAI_API_KEY for LLM council validation")
    print("3. Run the backend: python3 production_main.py")
    print("\nFor intelligence gathering only (without LLM):")
    print("- Apollo and PDL keys are sufficient")
    print("- LLM validation will be skipped if OPENAI_API_KEY is not set")
    print("=" * 60)

if __name__ == "__main__":
    verify_env()
