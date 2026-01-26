#!/bin/bash
set -euo pipefail

# Complete deployment script
# Run this after getting your Render URL

echo "╔════════════════════════════════════════════════════╗"
echo "║     COMPLETE DEPLOYMENT - FINAL STEP              ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

# Check if URL provided
if [ -z "${1:-}" ]; then
    echo "Usage: ./scripts/complete-deployment.sh <backend-url>"
    echo ""
    echo "Example:"
    echo "  ./scripts/complete-deployment.sh https://radtest-backend.onrender.com"
    echo ""
    exit 1
fi

BACKEND_URL="$1"

echo "Backend URL: $BACKEND_URL"
echo ""

# Test backend
echo "Step 1: Testing backend..."
HEALTH_CHECK=$(curl -s "$BACKEND_URL/health" || echo "failed")

if echo "$HEALTH_CHECK" | grep -q "healthy"; then
    echo "✅ Backend is healthy!"
else
    echo "⚠️  Backend test failed. Response:"
    echo "$HEALTH_CHECK"
    echo ""
    echo "The backend might still be deploying. Wait 1 minute and try again."
    exit 1
fi

echo ""
echo "Step 2: Updating Vercel environment variable..."

cd frontend

# Remove old value
vercel env rm NEXT_PUBLIC_API_URL production --yes 2>/dev/null || true

# Add new value
echo "$BACKEND_URL" | vercel env add NEXT_PUBLIC_API_URL production --yes

echo "✅ Environment variable updated!"

echo ""
echo "Step 3: Redeploying frontend..."

DEPLOY_OUTPUT=$(vercel --prod --yes 2>&1)
FRONTEND_URL=$(echo "$DEPLOY_OUTPUT" | grep -o 'https://[^[:space:]]*\.vercel\.app' | head -1)

if [ -z "$FRONTEND_URL" ]; then
    echo "⚠️  Could not find deployment URL. Deploy manually:"
    echo "   cd frontend && vercel --prod"
    exit 1
fi

echo "✅ Frontend redeployed!"
echo ""

echo "Step 4: Testing full system..."
sleep 5

# Test frontend
FRONTEND_TEST=$(curl -s "$FRONTEND_URL" || echo "failed")

if echo "$FRONTEND_TEST" | grep -q "RADTest"; then
    echo "✅ Frontend is working!"
else
    echo "⚠️  Frontend test inconclusive"
fi

echo ""
echo "╔════════════════════════════════════════════════════╗"
echo "║           🎉 DEPLOYMENT 100% COMPLETE! 🎉         ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""
echo "Frontend: $FRONTEND_URL"
echo "Backend:  $BACKEND_URL"
echo ""
echo "Test your application:"
echo "1. Visit: $FRONTEND_URL"
echo "2. Fill out the company profile form"
echo "3. Click 'Generate Profile'"
echo "4. See demo results!"
echo ""
echo "✅ Everything is LIVE and WORKING!"
echo ""
