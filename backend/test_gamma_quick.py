#!/usr/bin/env python3
"""Quick test to verify Gamma API works with template"""
import httpx
import json
import os
import time

API_KEY = os.getenv("GAMMA_API_KEY")

if not API_KEY:
    print("❌ ERROR: GAMMA_API_KEY not set in environment")
    exit(1)

print(f"✓ API Key found: {API_KEY[:20]}...")

headers = {
    "X-API-KEY": API_KEY,
    "Content-Type": "application/json"
}

# Test with template ID
payload = {
    "inputText": "# Test Slideshow\n\nThis is a test slideshow to verify the Gamma API integration.\n\n## Slide 2\n\nSome content here.",
    "textMode": "preserve",
    "format": "presentation",
    "templateId": "g_vsj27dcr73l1nv1"
}

print("\n🔄 Creating generation with template g_vsj27dcr73l1nv1...")
print(f"Payload: {json.dumps(payload, indent=2)}\n")

try:
    response = httpx.post(
        "https://public-api.gamma.app/v1.0/generations",
        json=payload,
        headers=headers,
        timeout=30
    )
    
    print(f"Response Status: {response.status_code}")
    print(f"Response Body:\n{json.dumps(response.json(), indent=2)}\n")
    
    if response.status_code != 200:
        print("❌ Failed to create generation")
        exit(1)
    
    result = response.json()
    generation_id = result.get("generationId") or result.get("generation_id") or result.get("id")
    
    if not generation_id:
        print("❌ No generationId in response!")
        print(f"Response keys: {list(result.keys())}")
        exit(1)
    
    print(f"✓ Generation created with ID: {generation_id}")
    
    # Poll for completion
    print("\n🔄 Polling for completion...")
    max_attempts = 60
    for i in range(max_attempts):
        time.sleep(2)
        
        status_resp = httpx.get(
            f"https://public-api.gamma.app/v1.0/generations/{generation_id}",
            headers=headers,
            timeout=30
        )
        
        status_data = status_resp.json()
        status = status_data.get("status")
        
        print(f"  Attempt {i+1}/{max_attempts}: {status}")
        
        if status == "completed":
            gamma_url = (
                status_data.get("gammaUrl") or
                status_data.get("url") or
                status_data.get("webUrl") or
                status_data.get("gamma_url")
            )
            
            print(f"\n✅ SUCCESS!")
            print(f"URL: {gamma_url}")
            print(f"\nFull response:\n{json.dumps(status_data, indent=2)}")
            exit(0)
        
        elif status == "failed":
            print(f"\n❌ Generation failed!")
            print(f"Response: {json.dumps(status_data, indent=2)}")
            exit(1)
    
    print("\n❌ Timeout waiting for completion")
    exit(1)

except Exception as e:
    print(f"\n❌ Exception: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
