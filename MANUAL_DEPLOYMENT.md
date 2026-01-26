# Manual Deployment Instructions

## Current Status

**Frontend**: ✅ Deployed at https://frontend-eight-rho-17.vercel.app
**Backend**: ⚠️ Ready to deploy (needs manual Railway setup)

## Why Manual Deployment Needed

The Railway token provided doesn't have the required permissions for automated deployment via CLI/API. This requires manual setup through the Railway dashboard.

## Deploy Backend to Railway (Manual Steps)

### Option 1: Railway Dashboard (Recommended)

1. **Go to Railway Dashboard**:
   - Visit: https://railway.app/dashboard
   - Login with your account

2. **Create New Project**:
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Connect your GitHub account if not already connected
   - Authorize Railway to access repositories

3. **Push Code to GitHub** (if not already):
   ```bash
   cd /workspaces/RADTest
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

4. **Deploy from GitHub**:
   - In Railway, select your RADTest repository
   - Select the `backend` directory
   - Railway will auto-detect Python and deploy

5. **Configure Environment** (Important):
   - Railway will use `demo_main.py` which works without API keys
   - Deployment should succeed automatically

6. **Get Your Backend URL**:
   - Railway will provide a URL like: `https://your-backend.railway.app`
   - Click on "Settings" → "Domains" to see your URL

### Option 2: Deploy via Railway CLI (Interactive)

```bash
# Install Railway CLI (already done)
# npm install -g @railway/cli

# Login interactively
railway login

# Navigate to backend
cd /workspaces/RADTest/backend

# Initialize project
railway init

# Deploy
railway up

# Get URL
railway domain
```

### Option 3: Deploy to Render.com (Alternative)

If Railway doesn't work, use Render.com:

1. **Go to Render Dashboard**:
   - Visit: https://render.com
   - Sign up/login

2. **Create New Web Service**:
   - Click "New" → "Web Service"
   - Connect GitHub repository
   - Select RADTest repository
   - Root Directory: `backend`

3. **Configure Build**:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn demo_main:app --host 0.0.0.0 --port $PORT`
   - Instance Type: Free

4. **Deploy**:
   - Click "Create Web Service"
   - Wait for deployment (2-3 minutes)
   - Get URL: `https://your-service.onrender.com`

### Option 4: Deploy to Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login
flyctl auth login

# Navigate to backend
cd /workspaces/RADTest/backend

# Launch app
flyctl launch --no-deploy

# Deploy
flyctl deploy
```

## Connect Frontend to Backend

Once backend is deployed:

1. **Get Backend URL** from Railway/Render/Fly.io

2. **Update Vercel Environment Variable**:
   - Go to: https://vercel.com/dashboard
   - Select your frontend project
   - Go to: Settings → Environment Variables
   - Add/Update:
     ```
     NEXT_PUBLIC_API_URL=<your-backend-url>
     ```

3. **Redeploy Frontend**:
   ```bash
   cd /workspaces/RADTest/frontend
   vercel --prod
   ```

4. **Test End-to-End**:
   - Visit: https://frontend-eight-rho-17.vercel.app
   - Fill out form
   - Submit request
   - See demo results!

## Backend Features (Demo Mode)

The deployed backend (`demo_main.py`) includes:

- ✅ `/health` - Health check endpoint
- ✅ `/profile-request` - Accepts company requests
- ✅ `/job-status/{job_id}` - Returns mock results
- ✅ CORS enabled for frontend
- ✅ Automatic API documentation at `/docs`
- ✅ Works without external API keys

Demo responses include:
- Mock company data
- Simulated confidence scores
- Fake slideshow URL
- Complete validated data structure

## Testing Backend

Once deployed, test with:

```bash
# Health check
curl https://your-backend-url/health

# Submit request
curl -X POST https://your-backend-url/profile-request \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test Corp",
    "domain": "test.com",
    "industry": "Technology",
    "requested_by": "user@example.com"
  }'

# Check job status (use job_id from previous response)
curl https://your-backend-url/job-status/demo-abc123
```

## Upgrade to Full Production

To use real API integrations instead of demo mode:

1. Get API keys for:
   - Apollo.io
   - PeopleDataLabs
   - OpenAI
   - Gamma
   - Supabase

2. Update Railway environment variables

3. Change start command to: `uvicorn src.main:app --host 0.0.0.0 --port $PORT`

4. Redeploy

See `BACKEND_DEPLOYMENT_GUIDE.md` for full production setup.

## Troubleshooting

**Problem**: Railway deployment fails
- Solution: Try Render.com or Fly.io as alternatives

**Problem**: Backend returns 502/503 errors
- Solution: Check Railway/Render logs, ensure demo_main.py is being used

**Problem**: CORS errors in browser
- Solution: Verify backend URL is correct in frontend env vars

**Problem**: Can't access Railway dashboard
- Solution: Make sure you're logged into the correct Railway account

## Quick Deploy Summary

1. Push code to GitHub (if not already)
2. Go to Railway/Render dashboard
3. Deploy from GitHub repository
4. Get backend URL
5. Update Vercel frontend env var
6. Done! Visit: https://frontend-eight-rho-17.vercel.app

---

**Note**: The demo backend works immediately without any API keys. Perfect for testing and demonstrations!
