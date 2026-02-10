#!/usr/bin/env python3
"""
Diagnostic script to inspect Gamma API response structure.
This will show us exactly what fields the API returns.
"""
import httpx
import json
import os
import time
import sys

API_KEY = os.getenv("GAMMA_API_KEY")

if not API_KEY:
    print("❌ ERROR: GAMMA_API_KEY not set in environment")
    sys.exit(1)

print(f"✓ API Key found: {API_KEY[:20]}...")
print()

headers = {
    "X-API-KEY": API_KEY,
    "Content-Type": "application/json"
}

# Minimal test payload
payload = {
    "inputText": "# Diagnostic Test\n\n## Slide 2\n\nThis is a minimal test to diagnose the URL field issue.\n\n---\n\n## Slide 3\n\nEnd of test.",
    "textMode": "preserve",
    "format": "presentation"
}

print("=" * 80)
print("GAMMA API DIAGNOSTIC TEST")
print("=" * 80)
print()

try:
    # Create generation
    print("[STEP 1] Creating generation...")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print()

    response = httpx.post(
        "https://public-api.gamma.app/v1.0/generations",
        json=payload,
        headers=headers,
        timeout=30
    )

    print(f"Response Status: {response.status_code}")

    if response.status_code not in [200, 201]:
        print(f"❌ Failed with status {response.status_code}")
        print(f"Response: {response.text}")
        sys.exit(1)

    result = response.json()
    print(f"Initial Response:")
    print(json.dumps(result, indent=2))
    print()

    generation_id = result.get("generationId") or result.get("generation_id") or result.get("id")

    if not generation_id:
        print("❌ No generationId in response!")
        print(f"Available keys: {list(result.keys())}")
        sys.exit(1)

    print(f"✓ Generation ID: {generation_id}")
    print()

    # Poll for completion
    print("[STEP 2] Polling for completion...")
    print("(This may take 30-60 seconds)")
    print()

    max_attempts = 60
    for i in range(max_attempts):
        time.sleep(2)

        status_resp = httpx.get(
            f"https://public-api.gamma.app/v1.0/generations/{generation_id}",
            headers=headers,
            timeout=30
        )

        if status_resp.status_code != 200:
            print(f"❌ Status check failed: {status_resp.status_code}")
            print(f"Response: {status_resp.text}")
            sys.exit(1)

        status_data = status_resp.json()
        status = status_data.get("status")

        elapsed = (i + 1) * 2
        print(f"  [{elapsed}s] Status: {status}")

        if status == "completed":
            print()
            print("=" * 80)
            print("✅ GENERATION COMPLETED")
            print("=" * 80)
            print()
            print("FULL API RESPONSE:")
            print(json.dumps(status_data, indent=2))
            print()
            print("=" * 80)
            print("FIELD ANALYSIS:")
            print("=" * 80)

            # Check each possible URL field
            url_fields = ["gammaUrl", "url", "webUrl", "gamma_url", "link", "shareUrl", "viewUrl"]
            found_url = None

            for field in url_fields:
                value = status_data.get(field)
                if value:
                    print(f"✓ {field}: {value}")
                    if not found_url:
                        found_url = value
                else:
                    print(f"✗ {field}: NOT PRESENT")

            print()
            print("All keys in response:")
            for key in status_data.keys():
                value = status_data[key]
                value_type = type(value).__name__
                if isinstance(value, str) and len(value) > 50:
                    print(f"  - {key} ({value_type}): {value[:50]}...")
                else:
                    print(f"  - {key} ({value_type}): {value}")

            print()
            print("=" * 80)

            if found_url:
                print(f"✅ URL FOUND: {found_url}")
            else:
                print("❌ NO URL FIELD FOUND IN RESPONSE!")
                print()
                print("Searching for any field containing 'gamma.app' or 'http':")
                for key, value in status_data.items():
                    if isinstance(value, str) and ("gamma.app" in value or "http" in value.lower()):
                        print(f"  Found in '{key}': {value}")

            print("=" * 80)
            sys.exit(0)

        elif status == "failed":
            print()
            print("❌ Generation failed!")
            print(json.dumps(status_data, indent=2))
            sys.exit(1)

        elif status in ["pending", "processing", "generating"]:
            # Continue polling
            continue
        else:
            print(f"  ⚠️ Unknown status: {status}")

    print()
    print("❌ Timeout after 120 seconds")
    sys.exit(1)

except Exception as e:
    print()
    print(f"❌ Exception: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
