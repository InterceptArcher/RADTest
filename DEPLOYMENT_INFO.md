# RADTest Deployment Information

## Frontend Deployment ✅ COMPLETE

**Deployment Date**: January 26, 2026
**Platform**: Vercel
**Status**: Successfully Deployed

### Production URLs
- **Primary URL**: https://frontend-ngjrydys8-fsilva7456s-projects.vercel.app
- **Alias URL**: https://frontend-eight-rho-17.vercel.app

### Deployment Details
- **Project**: fsilva7456s-projects/frontend
- **Build Time**: ~50 seconds
- **Build Status**: ✓ Success
- **Static Pages**: 4 pages generated
- **Bundle Size**: 108 KB First Load JS

### Next Steps for Frontend
1. Set backend API URL in Vercel dashboard:
   - Go to: https://vercel.com/fsilva7456s-projects/frontend/settings/environment-variables
   - Add: `NEXT_PUBLIC_API_URL` with your Railway backend URL
   - Redeploy to apply environment variable

---

## Backend Deployment ⚠️ REQUIRES API KEYS

**Platform**: Railway
**Status**: Awaiting Configuration

### Required Environment Variables

The backend requires the following API keys and credentials to be set:

```bash
# Railway Configuration
RAILWAY_WORKER_URL=<worker-service-url>
RAILWAY_API_TOKEN=<railway-api-token>
RAILWAY_PROJECT_ID=<railway-project-id>
RAILWAY_ENVIRONMENT_ID=<railway-environment-id>
RAILWAY_SERVICE_ID=<railway-service-id>

# Supabase Database
SUPABASE_URL=<your-supabase-project-url>
SUPABASE_KEY=<your-supabase-anon-key>

# Intelligence APIs
APOLLO_API_KEY=<your-apollo-io-key>
PDL_API_KEY=<your-peopledatalabs-key>

# LLM Provider
OPENAI_API_KEY=<your-openai-api-key>

# Slideshow Generation
GAMMA_API_KEY=<your-gamma-api-key>
```

### Backend Deployment Steps

1. **Install Railway CLI**:
   ```bash
   npm i -g @railway/cli
   ```

2. **Login to Railway**:
   ```bash
   railway login
   ```

3. **Navigate to backend**:
   ```bash
   cd backend
   ```

4. **Initialize Railway project**:
   ```bash
   railway init
   ```

5. **Set environment variables** in Railway dashboard or via CLI:
   ```bash
   railway variables set APOLLO_API_KEY=<value>
   railway variables set PDL_API_KEY=<value>
   railway variables set SUPABASE_URL=<value>
   railway variables set SUPABASE_KEY=<value>
   railway variables set OPENAI_API_KEY=<value>
   railway variables set GAMMA_API_KEY=<value>
   # ... set all other required variables
   ```

6. **Deploy**:
   ```bash
   railway up
   ```

7. **Get deployment URL**:
   ```bash
   railway domain
   ```

8. **Update frontend** with backend URL (step 1 above)

---

## Testing Deployment

### Frontend Only (Current State)
The frontend is live and accessible at the URLs above. However:
- ⚠️ API calls will fail until backend is deployed
- ⚠️ Form submissions will show connection errors
- ✓ UI and form validation work correctly

### Full System (After Backend Deployment)
Once backend is deployed and API URL is configured:
1. Visit frontend URL
2. Fill in company profile form
3. Submit request
4. View processing progress
5. See results and slideshow link

---

## Deployment Scripts Created

### Frontend Script
Location: `./scripts/deploy-frontend-vercel.sh`

Features:
- Installs dependencies
- Runs tests
- Builds application
- Deploys to Vercel
- Outputs deployment URL

### Backend Script
Location: `./scripts/deploy-backend-railway.sh`

Features:
- Guides through Railway setup
- Lists required environment variables
- Provides deployment commands

---

## Quick Commands

### Check Frontend Deployment
```bash
curl https://frontend-eight-rho-17.vercel.app
```

### View Frontend Logs
```bash
vercel logs https://frontend-ngjrydys8-fsilva7456s-projects.vercel.app
```

### Redeploy Frontend
```bash
cd frontend
vercel --prod
```

---

## Cost Considerations

### Vercel (Frontend)
- **Plan**: Hobby (Free)
- **Bandwidth**: Unlimited
- **Builds**: Unlimited
- **Functions**: Not used

### Railway (Backend - When Deployed)
- **Plan**: Pay-as-you-go
- **Cost**: Based on usage
- **Ephemeral Workers**: Billed per execution time
- **Estimated**: ~$5-20/month for light usage

### External APIs (When Active)
- **Apollo.io**: Varies by plan
- **PeopleDataLabs**: Pay-per-request
- **OpenAI**: Pay-per-token
- **Gamma**: Varies by plan
- **Supabase**: Free tier available

---

## Troubleshooting

### Frontend Issues

**Problem**: Blank page or loading forever
**Solution**: Check browser console for errors, verify API URL is set

**Problem**: Form validation not working
**Solution**: Clear cache and reload page

**Problem**: API connection errors
**Solution**: Backend needs to be deployed and URL configured

### Backend Issues (When Deploying)

**Problem**: Environment variable errors
**Solution**: Verify all required variables are set in Railway dashboard

**Problem**: Database connection fails
**Solution**: Check Supabase URL and key are correct

**Problem**: API rate limits
**Solution**: Check Apollo.io and PDL quotas

---

## Security Notes

✅ No secrets committed to repository
✅ All credentials via environment variables
✅ HTTPS enforced on all deployments
✅ Environment variables isolated per deployment

⚠️ Remember to:
- Rotate API keys regularly
- Use separate keys for dev/prod
- Monitor API usage and costs
- Set up billing alerts

---

## Support & Documentation

- Frontend Code: `/frontend`
- Backend Code: `/backend`
- Architecture: `ARCHITECTURE.md`
- Quick Start: `QUICKSTART.md`
- Main README: `README.md`

---

**Deployment completed by**: Claude Code
**Date**: January 26, 2026
