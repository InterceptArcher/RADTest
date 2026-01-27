# Render Environment Setup

This guide helps you automatically configure environment variables for your RADTest backend on Render.com.

## Quick Setup (Automated)

### Step 1: Get Your Render API Key

1. Go to https://dashboard.render.com/account
2. Click **"API Keys"** in the left sidebar
3. Click **"Create API Key"** or copy an existing one
4. Copy the API key (starts with `rnd_`)

### Step 2: Run Configuration Script

```bash
# Set your Render API key
export RENDER_API_KEY='rnd_your_api_key_here'

# Run the configuration script
./scripts/configure-render-env.sh
```

The script will:
- ✅ Find your `radtest-backend` service
- ✅ Configure environment variables from `.env.production`
- ✅ Trigger an automatic deployment
- ✅ Provide deployment status and URL

### Step 3: Verify Deployment

Wait 2-3 minutes for deployment, then test:

```bash
curl https://radtest-backend.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "mode": "production",
  "api_status": {
    "apollo": "configured",
    "peopledatalabs": "configured"
  }
}
```

---

## Manual Setup (Alternative)

If the automated script doesn't work:

1. Go to https://dashboard.render.com
2. Click on **"radtest-backend"**
3. Go to **"Environment"** tab
4. Add these variables:

```
APOLLO_API_KEY=Sat2ie-5bGpbtFwYBM7Dxg
PEOPLEDATALABS_API_KEY=428e3a8e7cd724ea74a8d0116ccd54a2b8220d2284ecab340ac7e723c71e5e84
PDL_API_KEY=428e3a8e7cd724ea74a8d0116ccd54a2b8220d2284ecab340ac7e723c71e5e84
PYTHON_VERSION=3.11.7
```

5. Click **"Save Changes"** - Render will auto-redeploy
6. Wait 2-3 minutes for deployment

---

## Testing with Real Companies

Once deployed, test with any company:

```bash
# Test Lululemon
curl -X POST https://radtest-backend.onrender.com/api/profile/submit \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Lululemon",
    "domain": "lululemon.com",
    "requested_by": "test@example.com"
  }'

# Expected: Returns job_id for tracking
```

Expected results for Lululemon:
- Employee count: 19,414
- Founded: 1998
- Headquarters: Vancouver, British Columbia
- Industry: Retail
- Geographic reach: 70+ countries

---

## Troubleshooting

### "Could not find service" Error
- Verify your service name is exactly `radtest-backend`
- Check your API key has correct permissions
- List services manually: `curl -H "Authorization: Bearer $RENDER_API_KEY" https://api.render.com/v1/services`

### "Invalid API Key" Error
- Regenerate API key at https://dashboard.render.com/account
- Make sure you're using the full key (starts with `rnd_`)

### APIs still show as "missing"
- Wait 2-3 minutes after deployment
- Check Render logs for errors
- Verify environment variables in Render dashboard

---

## What Gets Configured

The script configures these environment variables on your Render service:

| Variable | Purpose | Source |
|----------|---------|--------|
| `APOLLO_API_KEY` | Apollo.io company data | .env.production |
| `PEOPLEDATALABS_API_KEY` | PeopleDataLabs enrichment | .env.production |
| `PDL_API_KEY` | Alias for PDL (backward compatibility) | .env.production |
| `PYTHON_VERSION` | Python runtime version | Fixed: 3.11.7 |

---

## Support

- **Render Dashboard**: https://dashboard.render.com
- **Backend URL**: https://radtest-backend.onrender.com
- **API Docs**: https://radtest-backend.onrender.com/docs
