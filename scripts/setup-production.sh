#!/bin/bash
set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     RADTEST PRODUCTION SETUP - REAL DATA APIS            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if user has API keys
echo "This script will configure RADTest with real data sources."
echo ""
echo "You'll need API keys from:"
echo "  • Apollo.io ($49/month)"
echo "  • PeopleDataLabs ($99/month)"
echo "  • OpenAI (pay-as-you-go)"
echo "  • Supabase (free)"
echo "  • Gamma API (free tier: 400 credits)"
echo ""
read -p "Do you have all API keys ready? (y/n): " READY

if [ "$READY" != "y" ]; then
    echo ""
    echo "Please get your API keys first. See PRODUCTION_SETUP.md for details."
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "STEP 1: Collect API Keys"
echo "═══════════════════════════════════════════════════════════"
echo ""

read -p "Apollo.io API Key: " APOLLO_API_KEY
read -p "PeopleDataLabs API Key: " PEOPLEDATALABS_API_KEY
read -p "OpenAI API Key: " OPENAI_API_KEY
read -p "Supabase URL: " SUPABASE_URL
read -p "Supabase Anon Key: " SUPABASE_KEY
read -p "Gamma API Key: " GAMMA_API_KEY

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "STEP 2: Update Render Configuration"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Update render.yaml to use production main.py
cat > render.yaml << EOF
services:
  - type: web
    name: radtest-backend
    runtime: python
    env: python
    region: oregon
    plan: free
    branch: main
    buildCommand: pip install -r requirements.txt
    startCommand: cd backend/src && uvicorn main:app --host 0.0.0.0 --port \$PORT
    healthCheckPath: /health
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.7
      - key: APOLLO_API_KEY
        value: $APOLLO_API_KEY
      - key: PEOPLEDATALABS_API_KEY
        value: $PEOPLEDATALABS_API_KEY
      - key: OPENAI_API_KEY
        value: $OPENAI_API_KEY
      - key: SUPABASE_URL
        value: $SUPABASE_URL
      - key: SUPABASE_KEY
        value: $SUPABASE_KEY
      - key: GAMMA_API_KEY
        value: $GAMMA_API_KEY
      - key: DEBUG
        value: false
EOF

echo "✅ Updated render.yaml with production configuration"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "STEP 3: Set Up Supabase Tables"
echo "═══════════════════════════════════════════════════════════"
echo ""

cat > /tmp/supabase_schema.sql << 'EOF'
-- Raw data from APIs
CREATE TABLE IF NOT EXISTS raw_data (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_name TEXT NOT NULL,
  source TEXT NOT NULL,
  raw_data JSONB NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Normalized staging data
CREATE TABLE IF NOT EXISTS staging_normalized (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_name TEXT NOT NULL,
  field_name TEXT NOT NULL,
  candidate_values JSONB NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Final validated data
CREATE TABLE IF NOT EXISTS finalize_data (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_name TEXT NOT NULL,
  validated_data JSONB NOT NULL,
  confidence_scores JSONB NOT NULL,
  slideshow_url TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Job status tracking
CREATE TABLE IF NOT EXISTS job_status (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id TEXT UNIQUE NOT NULL,
  company_name TEXT NOT NULL,
  status TEXT NOT NULL,
  progress INTEGER DEFAULT 0,
  current_step TEXT,
  result JSONB,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
EOF

echo "SQL schema saved to /tmp/supabase_schema.sql"
echo ""
echo "To create tables in Supabase:"
echo "1. Go to: $SUPABASE_URL/project/_/sql"
echo "2. Copy and paste the contents of /tmp/supabase_schema.sql"
echo "3. Click 'Run'"
echo ""
read -p "Press Enter once you've created the tables..."

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "STEP 4: Commit and Deploy"
echo "═══════════════════════════════════════════════════════════"
echo ""

git add render.yaml
git commit -m "Configure production backend with real API keys

- Switch from demo_main.py to main.py (production)
- Add environment variables for all APIs
- Apollo.io: Company intelligence
- PeopleDataLabs: People analytics
- OpenAI: LLM validation with 10-20 agents
- Supabase: Data pipeline storage
- Gamma: Slideshow generation

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
"

git push origin main

echo "✅ Pushed to GitHub"
echo ""
echo "Render will now:"
echo "  • Detect the new configuration"
echo "  • Install dependencies"
echo "  • Start production backend"
echo "  • Use REAL data sources!"
echo ""
echo "This takes ~3 minutes..."

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "STEP 5: Update Render Environment Variables Manually"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "⚠️  IMPORTANT: render.yaml can't set secret env vars!"
echo ""
echo "Go to Render dashboard and add these manually:"
echo "  1. Go to: https://dashboard.render.com"
echo "  2. Click on: radtest-backend"
echo "  3. Click: Environment"
echo "  4. Add these variables:"
echo ""
echo "     APOLLO_API_KEY=$APOLLO_API_KEY"
echo "     PEOPLEDATALABS_API_KEY=$PEOPLEDATALABS_API_KEY"
echo "     OPENAI_API_KEY=$OPENAI_API_KEY"
echo "     SUPABASE_URL=$SUPABASE_URL"
echo "     SUPABASE_KEY=$SUPABASE_KEY"
echo "     GAMMA_API_KEY=$GAMMA_API_KEY"
echo ""
echo "  5. Click 'Save Changes'"
echo "  6. Render will auto-redeploy"
echo ""
read -p "Press Enter once you've added the environment variables..."

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              🎉 PRODUCTION SETUP COMPLETE! 🎉             ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Your backend now uses:"
echo "  ✅ Apollo.io for company data"
echo "  ✅ PeopleDataLabs for people analytics"
echo "  ✅ OpenAI GPT-4 with 10-20 validation agents"
echo "  ✅ Supabase for data pipeline"
echo "  ✅ Gamma API for slideshow generation"
echo ""
echo "Test with a real company to see accurate data!"
echo ""
