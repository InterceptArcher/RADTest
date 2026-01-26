# Backend Deployment Guide

## Current Status
⚠️ **Backend is NOT deployed** - Requires API keys configuration

## Why Backend Isn't Deployed Yet

The backend cannot function without valid API keys from multiple third-party services:
- Apollo.io (company intelligence)
- PeopleDataLabs (company data)
- OpenAI (LLM validation)
- Gamma (slideshow generation)
- Supabase (database)
- Railway (infrastructure)

These are paid services that require:
1. Account creation
2. API key generation
3. Billing setup
4. Usage configuration

## How to Deploy Backend

### Step 1: Obtain API Keys

#### Apollo.io
- Website: https://apollo.io
- Sign up for an account
- Navigate to Settings → API
- Generate API key
- Cost: Varies by plan (starts ~$49/month)

#### PeopleDataLabs
- Website: https://peopledatalabs.com
- Create account
- Go to Dashboard → API Keys
- Generate new key
- Cost: Pay-per-request or monthly plans

#### OpenAI
- Website: https://platform.openai.com
- Create account
- Go to API Keys section
- Create new secret key
- Cost: Pay-per-token (~$0.01-0.06 per 1K tokens)

#### Gamma
- Website: https://gamma.app
- Sign up for account
- Access API documentation
- Generate API key
- Cost: Varies by plan

#### Supabase
- Website: https://supabase.com
- Create new project
- Get project URL and anon key from Settings → API
- Cost: Free tier available, paid plans start at $25/month

### Step 2: Deploy to Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Navigate to backend directory
cd backend

# Initialize Railway project
railway init

# This will:
# - Create a new Railway project
# - Link your local code to Railway
# - Generate railway.json configuration
```

### Step 3: Set Environment Variables

In Railway dashboard (https://railway.app):

1. Navigate to your project
2. Click on "Variables" tab
3. Add all required environment variables:

```bash
# Railway Configuration
RAILWAY_WORKER_URL=https://your-worker-service.railway.app
RAILWAY_API_TOKEN=<get-from-railway-dashboard>
RAILWAY_PROJECT_ID=<your-project-id>
RAILWAY_ENVIRONMENT_ID=<your-environment-id>
RAILWAY_SERVICE_ID=<your-service-id>

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=<your-anon-key>

# Intelligence APIs
APOLLO_API_KEY=<your-apollo-key>
PDL_API_KEY=<your-pdl-key>

# LLM
OPENAI_API_KEY=<your-openai-key>

# Slideshow
GAMMA_API_KEY=<your-gamma-key>

# Application Settings
DEBUG=false
MAX_REQUEST_SIZE=1048576
WORKER_TIMEOUT=300
```

### Step 4: Deploy

```bash
# Deploy to Railway
railway up

# Get deployment URL
railway domain

# Example output: https://radtest-backend.railway.app
```

### Step 5: Configure Frontend

Once backend is deployed:

1. Go to Vercel dashboard: https://vercel.com/dashboard
2. Find your frontend project
3. Go to Settings → Environment Variables
4. Add or update:
   ```
   NEXT_PUBLIC_API_URL=https://radtest-backend.railway.app
   ```
5. Redeploy frontend:
   ```bash
   cd frontend
   vercel --prod
   ```

### Step 6: Test End-to-End

1. Visit frontend: https://frontend-eight-rho-17.vercel.app
2. Fill out company profile form
3. Submit request
4. Verify backend processes request
5. Check slideshow generation

## Cost Estimate

### Monthly Costs (Approximate)

| Service | Cost | Notes |
|---------|------|-------|
| Vercel (Frontend) | $0 | Free hobby plan |
| Railway (Backend) | $5-20 | Pay-as-you-go |
| Supabase | $0-25 | Free tier or pro |
| Apollo.io | $49+ | Depends on plan |
| PeopleDataLabs | $99+ | Pay-per-request |
| OpenAI | $10-50 | Usage-based |
| Gamma | $0-20 | Varies by plan |
| **TOTAL** | **$163-254/month** | For active usage |

### Cost Optimization

1. **Free Tier Usage**: Use free tiers where available
2. **Rate Limiting**: Implement rate limits to control API usage
3. **Caching**: Cache frequently requested data
4. **Batch Processing**: Process multiple requests together
5. **Development Mode**: Use mock data for development

## Alternative: Mock Backend for Demo

If you want to demo the frontend without full backend:

1. Create a simple mock API server
2. Return dummy data for profile requests
3. Simulate processing delays
4. Generate fake slideshow URLs

```bash
# Create simple mock server
cd backend
cat > mock_server.py << 'PYTHON'
from fastapi import FastAPI
import time
import asyncio

app = FastAPI()

@app.post("/profile-request")
async def mock_profile_request(request: dict):
    await asyncio.sleep(2)  # Simulate processing
    return {
        "status": "success",
        "job_id": "mock-job-123",
        "message": "Mock request submitted"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}
PYTHON

# Run mock server
uvicorn mock_server:app --port 8000
```

Then set frontend API URL to: http://localhost:8000

## Troubleshooting

### Common Issues

**Issue**: Railway deployment fails
- Check all environment variables are set
- Verify API keys are valid
- Check Railway logs for errors

**Issue**: Backend starts but crashes
- Missing environment variable
- Invalid API credentials
- Database connection failure

**Issue**: High costs
- Check API usage limits
- Implement rate limiting
- Use caching strategies
- Consider lower-tier plans

## Support

For deployment assistance:
1. Check Railway documentation: https://docs.railway.app
2. Review deployment logs
3. Verify all API keys are valid
4. Test each API endpoint individually

---

**Note**: The backend code is complete and production-ready. Only API key configuration is needed for deployment.
