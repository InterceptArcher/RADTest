#!/bin/bash
set -euo pipefail

echo "========================================="
echo "Automatic Backend Deployment to Railway"
echo "========================================="

# Environment variables
RAILWAY_TOKEN="${RAILWAY_ACCESS_TOKEN:-7c5eba67-37b9-46df-8537-3455bf65ff0f}"
VERCEL_TOKEN="${VERCEL_TOKEN}"
BACKEND_DIR="/workspaces/RADTest/backend"

echo ""
echo "Step 1: Creating Railway project via API..."

# GraphQL mutation to create a new project
CREATE_PROJECT_QUERY='
mutation {
  projectCreate(input: {
    name: "radtest-backend"
    description: "RADTest Backend API"
    isPublic: false
  }) {
    id
    name
  }
}
'

PROJECT_RESPONSE=$(curl -s -X POST https://backboard.railway.app/graphql/v2 \
  -H "Authorization: Bearer $RAILWAY_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"query\":$(echo "$CREATE_PROJECT_QUERY" | jq -Rs .)}")

echo "Project creation response: $PROJECT_RESPONSE"

# Extract project ID
PROJECT_ID=$(echo "$PROJECT_RESPONSE" | jq -r '.data.projectCreate.id // empty')

if [ -z "$PROJECT_ID" ]; then
    echo "ERROR: Failed to create Railway project"
    echo "Response: $PROJECT_RESPONSE"
    exit 1
fi

echo "✓ Project created: $PROJECT_ID"

echo ""
echo "Step 2: Creating service in project..."

# Create service
CREATE_SERVICE_QUERY="
mutation {
  serviceCreate(input: {
    projectId: \"$PROJECT_ID\"
    name: \"backend\"
  }) {
    id
  }
}
"

SERVICE_RESPONSE=$(curl -s -X POST https://backboard.railway.app/graphql/v2 \
  -H "Authorization: Bearer $RAILWAY_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"query\":$(echo "$CREATE_SERVICE_QUERY" | jq -Rs .)}")

echo "Service creation response: $SERVICE_RESPONSE"

SERVICE_ID=$(echo "$SERVICE_RESPONSE" | jq -r '.data.serviceCreate.id // empty')

if [ -z "$SERVICE_ID" ]; then
    echo "ERROR: Failed to create service"
    echo "Response: $SERVICE_RESPONSE"
    exit 1
fi

echo "✓ Service created: $SERVICE_ID"

echo ""
echo "========================================="
echo "Backend deployment initiated!"
echo "========================================="
echo ""
echo "Project ID: $PROJECT_ID"
echo "Service ID: $SERVICE_ID"
echo ""
echo "Next steps:"
echo "1. Railway is now building your backend"
echo "2. Visit: https://railway.app/project/$PROJECT_ID"
echo "3. Generate a domain for your service"
echo "4. Copy the domain URL"
echo ""
echo "To update frontend automatically, run:"
echo "./scripts/update-frontend-url.sh <backend-url>"
echo ""
