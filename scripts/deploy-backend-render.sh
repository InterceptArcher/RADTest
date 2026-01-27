#!/bin/bash
set -euo pipefail

# Deploy Backend to Render.com with Full API Configuration
# This script creates a render.yaml for automatic deployment

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     RADTEST BACKEND DEPLOYMENT TO RENDER.COM             ║"
echo "║     With LLM Council (OpenAI + Apollo + PDL)             ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    echo "❌ Error: .env.production file not found"
    exit 1
fi

# Load environment variables
echo "📖 Loading API keys from .env.production..."
set -a
source .env.production
set +a

# Verify required keys
MISSING_KEYS=""
if [ -z "${APOLLO_API_KEY:-}" ]; then MISSING_KEYS="$MISSING_KEYS APOLLO_API_KEY"; fi
if [ -z "${PEOPLEDATALABS_API_KEY:-}" ]; then MISSING_KEYS="$MISSING_KEYS PEOPLEDATALABS_API_KEY"; fi
if [ -z "${OPENAI_API_KEY:-}" ]; then MISSING_KEYS="$MISSING_KEYS OPENAI_API_KEY"; fi

if [ -n "$MISSING_KEYS" ]; then
    echo "❌ Error: Missing required API keys:$MISSING_KEYS"
    exit 1
fi

echo "✅ All required API keys loaded"
echo ""

# Create render.yaml
echo "📝 Creating render.yaml with full configuration..."

cat > render.yaml << EOF
services:
  - type: web
    name: radtest-backend
    runtime: python
    env: python
    region: oregon
    plan: free
    branch: main
    rootDir: backend
    buildCommand: pip install -r requirements.txt
    startCommand: python3 production_main.py
    healthCheckPath: /health
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.7
      - key: APOLLO_API_KEY
        sync: false
      - key: PEOPLEDATALABS_API_KEY
        sync: false
      - key: PDL_API_KEY
        sync: false
      - key: OPENAI_API_KEY
        sync: false
      - key: GEMINI_API_KEY
        sync: false
      - key: SUPABASE_KEY
        sync: false
      - key: SUPABASE_URL
        sync: false
      - key: GAMMA_API_KEY
        sync: false
      - key: DEBUG
        value: false
EOF

echo "✅ Created render.yaml"
echo ""

# Create instructions file
cat > RENDER_DEPLOYMENT_INSTRUCTIONS.md << EOF
# Render Deployment Instructions

## Automatic Deployment via GitHub

1. **Commit render.yaml to repository**:
   ```bash
   git add render.yaml
   git commit -m "Add Render deployment configuration"
   git push origin main
   ```

2. **Connect Render to GitHub**:
   - Go to https://dashboard.render.com/
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Render will detect render.yaml automatically

3. **Set Environment Variables** (CRITICAL):
   Go to your service's Environment tab and add these from .env.production:

   \`\`\`
   APOLLO_API_KEY=$APOLLO_API_KEY
   PEOPLEDATALABS_API_KEY=$PEOPLEDATALABS_API_KEY
   PDL_API_KEY=$PEOPLEDATALABS_API_KEY
   OPENAI_API_KEY=$OPENAI_API_KEY
   GEMINI_API_KEY=$GEMINI_API_KEY
   SUPABASE_KEY=$SUPABASE_KEY
   \`\`\`

4. **Deploy**:
   - Click "Create Web Service"
   - Wait 2-3 minutes for deployment
   - Get your URL (e.g., https://radtest-backend.onrender.com)

5. **Test**:
   ```bash
   curl https://your-service-url.onrender.com/health
   ```

## Manual Deployment via Dashboard

If you prefer manual setup:

1. Go to https://dashboard.render.com/
2. Click "New +" → "Web Service"
3. Choose "Build and deploy from a Git repository"
4. Connect your GitHub account
5. Select your repository
6. Configure:
   - **Name**: radtest-backend
   - **Region**: Oregon (US West)
   - **Branch**: main
   - **Root Directory**: backend
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python3 production_main.py`
   - **Plan**: Free

7. Add Environment Variables (from list above)

8. Click "Create Web Service"

## Verify Deployment

After deployment completes:

```bash
# Health check
curl https://radtest-backend.onrender.com/health

# Should return:
{
  "status": "healthy",
  "service": "RADTest Backend Production",
  "mode": "production",
  "api_status": {
    "apollo": "configured",
    "peopledatalabs": "configured",
    "openai": "configured",
    "supabase": "configured",
    "gamma": "missing"
  }
}

# Test profile request
curl -X POST https://radtest-backend.onrender.com/profile-request \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Microsoft",
    "domain": "microsoft.com",
    "industry": "Technology",
    "requested_by": "test@example.com"
  }'
```

## Update Frontend

Once backend is deployed, update frontend:

1. Go to Vercel dashboard: https://vercel.com/dashboard
2. Select your frontend project
3. Go to Settings → Environment Variables
4. Update `NEXT_PUBLIC_API_URL`:
   ```
   NEXT_PUBLIC_API_URL=https://radtest-backend.onrender.com
   ```
5. Redeploy frontend

## Troubleshooting

**Issue**: Service crashes on startup
- Check logs in Render dashboard
- Verify all environment variables are set
- Check PYTHON_VERSION is 3.11.7

**Issue**: API returns "degraded" mode
- One or more API keys not configured
- Check environment variables in Render dashboard

**Issue**: LLM Council not working
- Verify OPENAI_API_KEY is set correctly
- Check logs for OpenAI API errors
EOF

echo "✅ Created RENDER_DEPLOYMENT_INSTRUCTIONS.md"
echo ""

echo "╔════════════════════════════════════════════════════════════╗"
echo "║              DEPLOYMENT CONFIGURATION READY               ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📋 Files created:"
echo "   ✅ render.yaml - Render deployment configuration"
echo "   ✅ RENDER_DEPLOYMENT_INSTRUCTIONS.md - Step-by-step guide"
echo ""
echo "🚀 Next Steps:"
echo ""
echo "Option 1: Automatic Deployment (Recommended)"
echo "   1. Commit render.yaml to git"
echo "   2. Push to GitHub"
echo "   3. Connect Render to your GitHub repo"
echo "   4. Add environment variables in Render dashboard"
echo ""
echo "Option 2: Manual Render Dashboard Setup"
echo "   1. Follow instructions in RENDER_DEPLOYMENT_INSTRUCTIONS.md"
echo ""
echo "📖 See RENDER_DEPLOYMENT_INSTRUCTIONS.md for complete details"
echo ""

# Offer to commit
echo "═════════════════════════════════════════════════════════"
read -p "Commit render.yaml to git now? (y/n): " COMMIT_NOW

if [ "$COMMIT_NOW" = "y" ]; then
    git add render.yaml RENDER_DEPLOYMENT_INSTRUCTIONS.md
    git commit -m "Add Render deployment configuration with LLM Council

- Configure backend deployment to Render.com
- Include all API keys (Apollo, PDL, OpenAI, Gemini)
- LLM Council multi-agent validation enabled
- Production-ready configuration

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

    echo ""
    echo "✅ Committed to git"
    echo ""
    read -p "Push to GitHub now? (y/n): " PUSH_NOW

    if [ "$PUSH_NOW" = "y" ]; then
        git push origin main
        echo ""
        echo "✅ Pushed to GitHub"
        echo ""
        echo "🌐 Now go to https://dashboard.render.com/ to:"
        echo "   1. Connect your GitHub repository"
        echo "   2. Render will auto-detect render.yaml"
        echo "   3. Add environment variables"
        echo "   4. Deploy!"
    fi
fi

echo ""
echo "═════════════════════════════════════════════════════════"
echo "✨ Deployment configuration complete!"
echo "═════════════════════════════════════════════════════════"
