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

   **Get all API keys from your local `.env.production` file**

   Go to your service's Environment tab in Render and add these variables:

   - `APOLLO_API_KEY` - From .env.production
   - `PEOPLEDATALABS_API_KEY` - From .env.production
   - `PDL_API_KEY` - Same value as PEOPLEDATALABS_API_KEY
   - `OPENAI_API_KEY` - From .env.production
   - `GEMINI_API_KEY` - From .env.production
   - `SUPABASE_KEY` - From .env.production
   - `SUPABASE_URL` - Your Supabase project URL

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

7. Add Environment Variables (from .env.production file)

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
