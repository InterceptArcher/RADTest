# Gamma API Setup Guide

## Overview

The Gamma API integration enables automatic slideshow generation from company intelligence data. This feature is now **fully operational** and tested.

## API Configuration

### Gamma API Details
- **Version**: v1.0 (Generally Available as of November 2025)
- **Base URL**: `https://public-api.gamma.app/v1.0/`
- **Authentication**: X-API-KEY header
- **Key Format**: `sk-gamma-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### Requirements
- Gamma Pro, Ultra, Team, or Business account
- API access enabled
- Valid API key

## Setup Instructions

### For Local Development

1. **Create .env file** in the backend directory:
   ```bash
   cd /workspaces/RADTest/backend
   ```

2. **Add Gamma API key** to .env file:
   ```bash
   GAMMA_API_KEY=sk-gamma-your-api-key-here
   ```

3. **Verify configuration**:
   ```bash
   python3 test_gamma_integration.py
   ```

   Expected output:
   ```
   ✅ Test PASSED - Gamma integration is working!
   Slideshow URL: https://gamma.app/docs/...
   ```

### For Production Deployment

**Render.com / Railway.app:**
1. Go to your service dashboard
2. Navigate to Environment Variables section
3. Add new variable:
   - **Name**: `GAMMA_API_KEY`
   - **Value**: `sk-gamma-your-api-key-here`
4. Save and redeploy

**Vercel (if running backend on Vercel):**
1. Go to Project Settings → Environment Variables
2. Add `GAMMA_API_KEY` for Production, Preview, and Development
3. Redeploy application

## How It Works

### 1. Generation Request
When a company profile is processed, the system:
- Formats company data as structured markdown
- Sends POST request to `/v1.0/generations`
- Receives a `generationId`

### 2. Polling for Completion
- Polls status endpoint every 2 seconds
- Checks for `status: "completed"`
- Maximum timeout: 120 seconds

### 3. Result Retrieval
On completion, receives:
```json
{
  "generationId": "...",
  "status": "completed",
  "gammaUrl": "https://gamma.app/docs/...",
  "credits": {
    "deducted": 51,
    "remaining": 3833
  }
}
```

## Markdown Format

The system generates slideshows with the following structure:

### Slide 1: Title
- Company name as main heading

### Slide 2: Company Overview
- Domain, Industry, Headquarters
- Employee count, Revenue, Founded year

### Slide 3: Key Metrics
- Detailed financial and operational metrics

### Slide 4: Leadership
- CEO, Founders, Key executives

### Slide 5: Technology Stack
- Core technologies and platforms used

### Slide 6: Market Presence
- Target market, Geographic reach
- Customer segments

### Slide 7: Contact Information
- Website, LinkedIn, Email
- Social media presence

### Slide 8: Data Quality
- Confidence score
- Number of data sources
- Validated fields count

## Troubleshooting

### Issue: "GAMMA_API_KEY not configured"
**Solution**: Ensure environment variable is set correctly and application is restarted

### Issue: "Generation timed out"
**Solution**:
- Check API key is valid
- Verify network connectivity to api.gamma.app
- Increase timeout in code if needed (current: 120 seconds)

### Issue: "No URL returned from completed generation"
**Solution**: This was caused by using unsupported `templateId` parameter. The Gamma API v1.0 does not support custom templates via API. Fixed by removing templateId from payload.

### Issue: "HTTP 400 - property templateId should not exist"
**Solution**: The `templateId` parameter is not supported by Gamma API v1.0. Templates must be applied through the Gamma web UI after generation, not during API creation.

### Issue: "HTTP 401 Unauthorized"
**Solution**:
- Verify API key format (should start with `sk-gamma-`)
- Check account has API access enabled
- Ensure key hasn't expired

### Issue: "HTTP 429 Too Many Requests"
**Solution**:
- API rate limit reached
- Wait before making more requests
- Consider implementing request queuing

## API Limits

- **Free tier**: Not available (requires paid account)
- **Rate limits**: Varies by plan tier
- **Generation time**: Typically 30-60 seconds
- **Credits**: Deducted per generation (usually 40-60 credits)

## Testing

### Run Integration Test
```bash
cd /workspaces/RADTest/backend
python3 test_gamma_integration.py
```

### Test with Custom Data
```python
from worker.gamma_slideshow import GammaSlideshowCreator
import asyncio
import os

async def test():
    api_key = os.getenv("GAMMA_API_KEY")
    creator = GammaSlideshowCreator(api_key)

    company_data = {
        "company_name": "Example Corp",
        "validated_data": {...},
        "confidence_score": 0.90
    }

    result = await creator.create_slideshow(company_data)
    print(result)

asyncio.run(test())
```

## Security Notes

⚠️ **IMPORTANT**:
- **NEVER** commit API keys to git
- **.env file is gitignored** - this is correct and required
- **Use environment variables** for all deployments
- **Rotate keys regularly** for security
- **Limit API key access** to only necessary services

## References

- **Official Docs**: https://developers.gamma.app/
- **Generate API**: https://developers.gamma.app/reference/generate-a-gamma
- **Parameters Guide**: https://developers.gamma.app/docs/generate-api-parameters-explained

## Status

✅ **FULLY OPERATIONAL** (as of 2026-01-29)
- Integration tested and verified
- Slideshow generation working
- Successfully generating presentations from company data
- Average generation time: 45-60 seconds
