#!/usr/bin/env python3
"""Direct test of Gamma API to debug response format"""
import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GAMMA_API_KEY")

# Step 1: Create generation
print("="*60)
print("STEP 1: Creating generation...")
print("="*60)

headers = {
    "X-API-KEY": API_KEY,
    "Content-Type": "application/json"
}

payload = {
    "inputText": "# Test Company\n\nA simple test presentation about a company.",
    "textMode": "preserve",
    "format": "presentation"
}

response = httpx.post(
    "https://public-api.gamma.app/v1.0/generations",
    json=payload,
    headers=headers,
    timeout=30
)

print(f"Status: {response.status_code}")
print(f"Response:\n{json.dumps(response.json(), indent=2)}")

result = response.json()
generation_id = result.get("generationId")

if not generation_id:
    print("ERROR: No generationId returned!")
    exit(1)

print(f"\nGeneration ID: {generation_id}")

# Step 2: Check status
print("\n" + "="*60)
print("STEP 2: Checking generation status...")
print("="*60)

status_response = httpx.get(
    f"https://public-api.gamma.app/v1.0/generations/{generation_id}",
    headers=headers,
    timeout=30
)

print(f"Status: {status_response.status_code}")
print(f"Response:\n{json.dumps(status_response.json(), indent=2)}")
