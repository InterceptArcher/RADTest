#!/bin/bash
set -euo pipefail

# Railway Backend Deployment Script
# This script assumes Railway CLI is installed and configured
# RAILWAY_TOKEN must be provided via environment variables

echo "========================================="
echo "RADTest Backend Deployment to Railway"
echo "========================================="

# Note: Railway deployment requires Railway CLI and project setup
# For this demo, we'll create a placeholder that guides manual deployment

echo ""
echo "Railway Backend Deployment Guide"
echo "================================="
echo ""
echo "To deploy the backend to Railway:"
echo ""
echo "1. Install Railway CLI:"
echo "   npm i -g @railway/cli"
echo ""
echo "2. Login to Railway:"
echo "   railway login"
echo ""
echo "3. Navigate to backend directory:"
echo "   cd backend"
echo ""
echo "4. Initialize Railway project:"
echo "   railway init"
echo ""
echo "5. Set environment variables in Railway dashboard:"
echo "   - APOLLO_API_KEY"
echo "   - PDL_API_KEY"
echo "   - SUPABASE_URL"
echo "   - SUPABASE_KEY"
echo "   - OPENAI_API_KEY"
echo "   - GAMMA_API_KEY"
echo "   - RAILWAY_WORKER_URL"
echo "   - RAILWAY_API_TOKEN"
echo "   - RAILWAY_PROJECT_ID"
echo "   - RAILWAY_ENVIRONMENT_ID"
echo "   - RAILWAY_SERVICE_ID"
echo ""
echo "6. Deploy:"
echo "   railway up"
echo ""
echo "7. Get the deployment URL:"
echo "   railway domain"
echo ""
echo "8. Update frontend environment variable with backend URL"
echo ""

# Check if Railway CLI is installed
if command -v railway &> /dev/null; then
    echo "✓ Railway CLI is installed"

    # Navigate to backend directory
    cd "$(dirname "$0")/../backend" || exit 1

    echo ""
    echo "Checking Railway project status..."

    if railway status 2>&1 | grep -q "Not logged in"; then
        echo "⚠ Not logged in to Railway"
        echo "Run: railway login"
        exit 1
    fi

    echo ""
    echo "Note: Actual deployment requires API keys to be set"
    echo "Use Railway dashboard to configure environment variables"
else
    echo "⚠ Railway CLI not installed"
    echo "Install with: npm i -g @railway/cli"
fi

echo ""
echo "========================================="
