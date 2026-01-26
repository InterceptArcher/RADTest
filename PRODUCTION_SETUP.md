# 🚀 Production Setup Guide - Real Data APIs

## Overview

This guide walks you through deploying the FULL production system with real data sources.

## Cost Breakdown

| Service | Cost | Purpose |
|---------|------|---------|
| Apollo.io | $49/month | Company intelligence data |
| PeopleDataLabs | $99/month | People & company analytics |
| OpenAI API | ~$20/month | LLM validation (10-20 agents) |
| Supabase | Free | Database for data pipeline |
| Gamma API | Free (400 credits) | Slideshow generation |
| Render.com | Free | Backend hosting |
| Vercel | Free | Frontend hosting |
| **Total** | **~$170/month** | Full production system |

---

## Step 1: Get API Keys

### Apollo.io
1. Go to: https://apollo.io
2. Sign up for **Growth plan** ($49/month)
3. Navigate to: Settings → Integrations → API
4. Copy your API key

### PeopleDataLabs
1. Go to: https://www.peopledatalabs.com/pricing
2. Sign up for **Developer plan** ($99/month)
3. Go to: Dashboard → API Keys
4. Copy your API key

### OpenAI
1. Go to: https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the key (starts with `sk-`)
4. Add billing: https://platform.openai.com/account/billing
5. Add minimum $5 credits

### Supabase
1. Go to: https://supabase.com/dashboard
2. Click "New project"
3. Name: `radtest-production`
4. Wait 2 minutes for setup
5. Go to: Settings → API
6. Copy:
   - Project URL
   - `anon` `public` key

### Gamma API
1. Go to: https://gamma.app/api
2. Sign up (free tier: 400 credits/month)
3. Get API key from dashboard

---

## Step 2: Configure Backend Environment

Once you have all API keys, I'll configure them in Render.

You'll need to provide:
```
APOLLO_API_KEY=<your-apollo-key>
PEOPLEDATALABS_API_KEY=<your-pdl-key>
OPENAI_API_KEY=<your-openai-key>
SUPABASE_URL=<your-supabase-url>
SUPABASE_KEY=<your-supabase-anon-key>
GAMMA_API_KEY=<your-gamma-key>
RAILWAY_API_TOKEN=<optional-if-using-workers>
```

---

## Step 3: Set Up Supabase Tables

I'll create these tables automatically:

```sql
-- Raw data from APIs
CREATE TABLE raw_data (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_name TEXT NOT NULL,
  source TEXT NOT NULL,
  raw_data JSONB NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Normalized staging data
CREATE TABLE staging_normalized (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_name TEXT NOT NULL,
  field_name TEXT NOT NULL,
  candidate_values JSONB NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Final validated data
CREATE TABLE finalize_data (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_name TEXT NOT NULL,
  validated_data JSONB NOT NULL,
  confidence_scores JSONB NOT NULL,
  slideshow_url TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Step 4: Deploy Production Backend

I'll:
1. Update Render to use `main.py` (production) instead of `demo_main.py`
2. Set all environment variables
3. Deploy with real API integrations

---

## Step 5: Test Full Pipeline

Test with a real company:
```
Company: Microsoft
Domain: microsoft.com
Industry: Technology

Expected Real Data:
✅ CEO: Satya Nadella
✅ Employees: 220,000+
✅ Revenue: $211B (2023)
✅ Founded: 1975
✅ HQ: Redmond, Washington
✅ Real technology stack
✅ Validated by 10-20 LLM agents
✅ Professional slideshow generated
```

---

## What Happens Behind the Scenes

```
1. User submits "Microsoft"
   ↓
2. Backend triggers Railway worker
   ↓
3. Worker queries Apollo.io & PeopleDataLabs in parallel
   ↓
4. Raw data stored in Supabase (raw_data table)
   ↓
5. 10-20 OpenAI agents validate each field
   ↓
6. LLM council resolves conflicts
   ↓
7. Validated data stored (finalize_data table)
   ↓
8. Gamma API generates slideshow
   ↓
9. User sees real, validated company profile!
```

---

## Ready to Start?

Provide your API keys and I'll configure everything automatically!
