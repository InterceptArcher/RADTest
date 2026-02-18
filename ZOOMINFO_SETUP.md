# ZoomInfo Contact Enrichment Setup Guide

## ✅ Status: FULLY INTEGRATED

Your system **already has ZoomInfo contact enrichment fully integrated**. You just need to verify the credentials on Render.

---

## How It Works

When you create a company profile request, the system automatically:

1. **Searches for contacts** at the target company using ZoomInfo's Contact Search API
   - Searches by management level (C-Level, VP, Director, Manager)
   - Searches by job titles (CEO, CTO, CFO, etc.)
   - Finds up to 25 contacts per company

2. **Enriches contact data** using ZoomInfo's Contact Enrich API
   - Full name, title, email
   - **Direct phone numbers** (directPhone, mobilePhone, companyPhone)
   - Contact accuracy score
   - Department and management level
   - LinkedIn profile URL

3. **Stores enriched contacts** in the job results
   - Available via `/api/status/{job_id}` endpoint
   - Included in stakeholder analysis
   - Used for slideshow generation

---

## Credentials Setup on Render

You've already added the credentials to Render. Here's how to verify:

### 1. Check Environment Variables on Render

Go to your Render dashboard:
- Navigate to your backend service
- Go to **Environment** tab
- Verify these variables are set:
  - ✅ `ZOOMINFO_CLIENT_ID`
  - ✅ `ZOOMINFO_CLIENT_SECRET`

### 2. Restart Backend Service

After adding environment variables, you MUST restart the service:
- Click **Manual Deploy** → **Deploy latest commit**
- OR Click **Restart Service**

This ensures the new environment variables are loaded.

### 3. Check Backend Logs

After restart, check the logs for:

```
==========================================
ENVIRONMENT VARIABLE STATUS AT STARTUP:
  ZOOMINFO_CLIENT_ID: SET
  ZOOMINFO_CLIENT_SECRET: SET
==========================================
```

If you see `MISSING` instead of `SET`, the credentials weren't loaded properly.

---

## Testing Contact Enrichment

### Option 1: Health Check Endpoint

Visit your backend URL:
```
https://your-backend.onrender.com/health
```

Look for:
```json
{
  "status": "healthy",
  "api_status": {
    "zoominfo": "configured"  ← Should say "configured", not "missing"
  }
}
```

### Option 2: Create Test Company Profile

Use your frontend or API to create a profile request:

```bash
curl -X POST https://your-backend.onrender.com/api/generate-profile \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "HP Inc",
    "domain": "hp.com",
    "industry": "Technology",
    "requested_by": "test@example.com"
  }'
```

Then check the job status:
```bash
curl https://your-backend.onrender.com/api/status/{job_id}
```

Look for `zoominfo_data` with contact information in the response.

### Option 3: Run Local Test Script

If you have ZoomInfo credentials in your local `.env` file:

```bash
python3 test_zoominfo_setup.py
```

This will:
- ✅ Verify credentials are loaded
- ✅ Test authentication
- ✅ Test contact search and enrichment
- ✅ Display sample contact data

---

## What Data Gets Enriched

### Company Data from ZoomInfo
- Employee count, revenue, growth metrics
- Technologies installed (tech stack)
- Industry classification (SIC, NAICS codes)
- Leadership (CEO, CFO, CTO names)
- Contact information (phone, fax)
- Social media profiles

### Contact Data from ZoomInfo
- **Name**: Full name, first name, last name
- **Title**: Job title (e.g., "VP of Engineering")
- **Email**: Corporate email address
- **Phone Numbers**:
  - Direct phone (personal desk line)
  - Mobile phone (cell phone)
  - Company phone (main switchboard)
- **LinkedIn**: Profile URL
- **Management Level**: C-Level, VP-Level, Director, Manager
- **Department**: Sales, Engineering, IT, etc.
- **Accuracy Score**: Data quality confidence (0-100)
- **Person ID**: ZoomInfo unique identifier

### Intent Signals from ZoomInfo
- Buying intent topics
- Intent scores and audience strength
- Research activity level

### Business Events (Scoops) from ZoomInfo
- Funding rounds
- Executive hires
- Office expansions
- Partnerships
- Product launches

### News from ZoomInfo
- Recent news articles
- Press releases
- Media coverage

---

## How to Access Enriched Contact Data

### 1. Via Job Status Endpoint

```bash
GET /api/status/{job_id}
```

Response includes:
```json
{
  "zoominfo_data": {
    "contacts": [
      {
        "name": "John Doe",
        "title": "VP of Engineering",
        "email": "john.doe@company.com",
        "direct_phone": "+1-555-0123",
        "mobile_phone": "+1-555-0124",
        "management_level": "VP-Level",
        "department": "Engineering",
        "contact_accuracy_score": 95
      }
    ]
  },
  "stakeholders_data": [
    {
      "role_type": "CTO",
      "name": "Jane Smith",
      "email": "jane.smith@company.com",
      "phone": "+1-555-0125",
      "source": "zoominfo"
    }
  ]
}
```

### 2. Via Debug Endpoint

```bash
GET /api/debug/{job_id}
```

Returns comprehensive data including:
- `zoominfo_company`: Company firmographic data
- `zoominfo_contacts`: All enriched contacts
- `zoominfo_intent`: Intent signals
- `zoominfo_scoops`: Business events
- `zoominfo_news`: News articles
- `zoominfo_tech`: Technology stack

### 3. In Slideshow Generation

ZoomInfo contact data is automatically included in slideshow:
- **Stakeholder Profiles section**: Shows key decision makers
- **Contact Information section**: Displays phone numbers
- **Buying Signals section**: Shows intent and news from ZoomInfo

---

## Troubleshooting

### Issue: "zoominfo": "missing" in health check

**Solution:**
1. Verify environment variables are set on Render
2. Restart backend service
3. Check logs for "ZOOMINFO_CLIENT_ID: SET"

### Issue: No contact data in job results

**Possible causes:**
1. **Invalid credentials**: Check logs for authentication errors
2. **Invalid domain**: ZoomInfo requires valid company domain
3. **Rate limit**: ZoomInfo has 25 req/sec limit (handled automatically)
4. **No data available**: Company may not be in ZoomInfo database

**Check logs for:**
```
ZoomInfo returned 0 contacts
```

### Issue: Authentication errors

**Check logs for:**
```
ZoomInfo authentication failed: HTTP 401
```

**Solution:**
- Verify CLIENT_ID and CLIENT_SECRET are correct
- Check if credentials have expired
- Ensure credentials have API access enabled

### Issue: Contact data missing phone numbers

**Explanation:**
- Not all contacts have phone numbers in ZoomInfo
- Use `contact_accuracy_score` to identify high-quality records
- Direct/mobile phones may not be available for all contacts

---

## API Credentials Options

### Option 1: OAuth (Recommended) ✅

Use CLIENT_ID + CLIENT_SECRET for automatic token refresh:

```bash
ZOOMINFO_CLIENT_ID=your_client_id
ZOOMINFO_CLIENT_SECRET=your_client_secret
```

**Benefits:**
- ✅ Automatic token refresh
- ✅ Tokens expire but system auto-renews
- ✅ More secure

### Option 2: Static Token

Use ACCESS_TOKEN directly:

```bash
ZOOMINFO_ACCESS_TOKEN=your_access_token
```

**Limitations:**
- ⚠️ Token expires after ~1 hour
- ⚠️ No automatic refresh
- ⚠️ Must manually update when expired

**We recommend Option 1 (OAuth) for production.**

---

## Code Integration (Already Done)

Your system already has full integration:

### 1. Environment Variables Loaded
**File**: `backend/production_main.py` (lines 102-104)
```python
ZOOMINFO_CLIENT_ID = os.getenv("ZOOMINFO_CLIENT_ID")
ZOOMINFO_CLIENT_SECRET = os.getenv("ZOOMINFO_CLIENT_SECRET")
ZOOMINFO_ACCESS_TOKEN = os.getenv("ZOOMINFO_ACCESS_TOKEN")
```

### 2. Client Initialization
**File**: `backend/production_main.py` (lines 776-792)
```python
def _get_zoominfo_client():
    if ZOOMINFO_CLIENT_ID and ZOOMINFO_CLIENT_SECRET:
        return ZoomInfoClient(
            client_id=ZOOMINFO_CLIENT_ID,
            client_secret=ZOOMINFO_CLIENT_SECRET
        )
    # ... fallback to access token
```

### 3. Contact Enrichment Called
**File**: `backend/production_main.py` (lines 813, 1043-1053)
```python
# In enrichment pipeline
contacts_task = zi_client.search_and_enrich_contacts(domain=domain)

# Results stored
zoominfo_data["contacts"] = zoominfo_contacts
jobs_store[job_id]["zoominfo_data"] = zoominfo_data
```

### 4. Full ZoomInfo Client
**File**: `backend/worker/zoominfo_client.py`

Implements:
- ✅ OAuth authentication with auto-refresh
- ✅ Contact search by management level + job title
- ✅ Contact enrichment with phone numbers
- ✅ Company enrichment
- ✅ Intent signals
- ✅ Scoops (business events)
- ✅ News search
- ✅ Technology enrichment
- ✅ Rate limiting (25 req/sec)
- ✅ Error handling and retries

---

## Next Steps

1. **Verify Render Setup**:
   - ✅ Check environment variables are set
   - ✅ Restart backend service
   - ✅ Check logs show "ZOOMINFO_CLIENT_ID: SET"

2. **Test Contact Enrichment**:
   - ✅ Hit `/health` endpoint - should show "configured"
   - ✅ Create test company profile
   - ✅ Check job status for `zoominfo_data.contacts`

3. **Use in Production**:
   - ✅ Contact data auto-enriches for every company profile
   - ✅ No code changes needed
   - ✅ Enriched contacts show in slideshow automatically

---

## Questions?

Contact enrichment is **fully operational**. Just verify your Render credentials and restart the service!

If you see any errors, check the backend logs for specific ZoomInfo API error messages.
