#!/bin/bash
set -euo pipefail

# Render Environment Configuration Script
# Automatically configures environment variables for RADTest backend on Render.com

echo "🔧 Render Environment Configuration Script"
echo "=========================================="
echo ""

# Check for Render API key
if [ -z "${RENDER_API_KEY:-}" ]; then
    echo "❌ Error: RENDER_API_KEY environment variable not set"
    echo ""
    echo "To get your Render API key:"
    echo "1. Go to https://dashboard.render.com/account"
    echo "2. Click 'API Keys' in the left sidebar"
    echo "3. Create a new API key or copy existing one"
    echo ""
    echo "Then run:"
    echo "  export RENDER_API_KEY='your-api-key'"
    echo "  ./scripts/configure-render-env.sh"
    exit 1
fi

# Service configuration
SERVICE_NAME="radtest-backend"

echo "🔍 Finding service ID for '$SERVICE_NAME'..."
echo ""

# Get all services
SERVICES_RESPONSE=$(curl -s -H "Authorization: Bearer $RENDER_API_KEY" \
    "https://api.render.com/v1/services?limit=20")

# Extract service ID
SERVICE_ID=$(echo "$SERVICES_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for service in data:
        if isinstance(service, dict) and service.get('service', {}).get('name') == '$SERVICE_NAME':
            print(service['service']['id'])
            sys.exit(0)
    print('NOT_FOUND')
except Exception as e:
    print('ERROR', file=sys.stderr)
    print(str(e), file=sys.stderr)
    sys.exit(1)
")

if [ "$SERVICE_ID" = "NOT_FOUND" ] || [ -z "$SERVICE_ID" ]; then
    echo "❌ Error: Could not find service '$SERVICE_NAME'"
    echo ""
    echo "Available services:"
    echo "$SERVICES_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for item in data:
        if isinstance(item, dict):
            service = item.get('service', {})
            print(f\"  - {service.get('name', 'unknown')} ({service.get('id', 'unknown')})\")
except:
    print('Could not parse services list')
"
    echo ""
    echo "Please verify the service name or manually set SERVICE_ID:"
    echo "  export SERVICE_ID='srv-xxxxx'"
    exit 1
fi

echo "✅ Found service: $SERVICE_ID"
echo ""

# Read API keys from .env.production
echo "📖 Reading API keys from .env.production..."
if [ ! -f ".env.production" ]; then
    echo "❌ Error: .env.production file not found"
    exit 1
fi

# Source the .env.production file
set -a
source .env.production
set +a

# Validate required variables
if [ -z "${PEOPLEDATALABS_API_KEY:-}" ] || [ -z "${APOLLO_API_KEY:-}" ]; then
    echo "❌ Error: Required API keys not found in .env.production"
    echo "   Need: APOLLO_API_KEY, PEOPLEDATALABS_API_KEY"
    exit 1
fi

echo "✅ API keys loaded"
echo ""

# Prepare environment variables payload
echo "🚀 Updating environment variables on Render..."
echo ""

# Update environment variables
RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT \
    -H "Authorization: Bearer $RENDER_API_KEY" \
    -H "Content-Type: application/json" \
    "https://api.render.com/v1/services/$SERVICE_ID/env-vars" \
    -d "{
        \"envVars\": [
            {
                \"key\": \"APOLLO_API_KEY\",
                \"value\": \"$APOLLO_API_KEY\"
            },
            {
                \"key\": \"PEOPLEDATALABS_API_KEY\",
                \"value\": \"$PEOPLEDATALABS_API_KEY\"
            },
            {
                \"key\": \"PDL_API_KEY\",
                \"value\": \"$PEOPLEDATALABS_API_KEY\"
            },
            {
                \"key\": \"PYTHON_VERSION\",
                \"value\": \"3.11.7\"
            }
        ]
    }")

# Extract status code
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
    echo "✅ Environment variables updated successfully!"
    echo ""
    echo "📋 Updated variables:"
    echo "   - APOLLO_API_KEY: ${APOLLO_API_KEY:0:10}..."
    echo "   - PEOPLEDATALABS_API_KEY: ${PEOPLEDATALABS_API_KEY:0:10}..."
    echo "   - PDL_API_KEY: ${PEOPLEDATALABS_API_KEY:0:10}..."
    echo "   - PYTHON_VERSION: 3.11.7"
    echo ""

    # Trigger deploy
    echo "🔄 Triggering deployment..."
    DEPLOY_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
        -H "Authorization: Bearer $RENDER_API_KEY" \
        "https://api.render.com/v1/services/$SERVICE_ID/deploys")

    DEPLOY_HTTP_CODE=$(echo "$DEPLOY_RESPONSE" | tail -n1)
    DEPLOY_BODY=$(echo "$DEPLOY_RESPONSE" | sed '$d')

    if [ "$DEPLOY_HTTP_CODE" = "201" ] || [ "$DEPLOY_HTTP_CODE" = "200" ]; then
        echo "✅ Deployment triggered successfully!"
        echo ""
        DEPLOY_ID=$(echo "$DEPLOY_BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', 'unknown'))" 2>/dev/null || echo "unknown")
        echo "📦 Deploy ID: $DEPLOY_ID"
        echo ""
        echo "🌐 Your backend will be live at:"
        echo "   https://radtest-backend.onrender.com"
        echo ""
        echo "⏳ Deployment typically takes 2-3 minutes"
        echo "   Check status: https://dashboard.render.com/web/$SERVICE_ID"
        echo ""
        echo "✨ Once deployed, test with:"
        echo "   curl https://radtest-backend.onrender.com/health"
        echo ""
    else
        echo "⚠️  Warning: Could not trigger automatic deployment (HTTP $DEPLOY_HTTP_CODE)"
        echo "   Please manually deploy from: https://dashboard.render.com/web/$SERVICE_ID"
        echo ""
        echo "Response: $DEPLOY_BODY"
    fi
else
    echo "❌ Error: Failed to update environment variables (HTTP $HTTP_CODE)"
    echo ""
    echo "Response:"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    exit 1
fi

echo "=========================================="
echo "✅ Configuration complete!"
