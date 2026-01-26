# 🔧 Fix Backend 502 Error

## Current Status

✅ **Backend Deployed**: radtest-production.up.railway.app
❌ **Backend Status**: 502 - Application failed to respond
✅ **Frontend Updated**: Environment variable set
⏳ **Frontend**: Needs redeploy

## What's Wrong

The backend is deployed to Railway but isn't starting correctly. This is usually because:

1. **Start command is wrong**
2. **PORT environment variable not set**
3. **Dependencies not installing**
4. **Python version mismatch**

## 🚀 FIX IT NOW (3 Minutes)

### Option 1: Fix Railway Configuration (Recommended)

Go to your Railway dashboard: https://railway.app/project

1. **Click on your backend service**

2. **Go to Settings tab**

3. **Check "Start Command":**
   - Should be: `uvicorn demo_main:app --host 0.0.0.0 --port $PORT`
   - If it's different, update it

4. **Check "Root Directory":**
   - Should be: `backend`
   - If it's blank or wrong, set it to `backend`

5. **Go to Variables tab**

6. **Make sure PORT is set:**
   - Railway usually sets this automatically
   - If not there, add: `PORT` = `8000`

7. **Redeploy:**
   - Click "Deployments" tab
   - Click "Redeploy" on latest deployment

8. **Wait 2 minutes** for redeployment

### Option 2: Check Railway Logs

1. In Railway dashboard, click your service
2. Click "Deployments" tab
3. Click on the latest deployment
4. Look at the logs for errors

**Common errors:**
- `ModuleNotFoundError` → Dependencies not installed
- `PORT not defined` → Need to set PORT variable
- `demo_main not found` → Root directory is wrong

### Option 3: Redeploy with Correct Settings

If nothing works, redeploy from scratch:

1. **Delete the current service** in Railway
2. **Create new service:**
   - Click "New" → "GitHub Repo"
   - Select: InterceptArcher/RADTest
   - Root Directory: `backend`
3. **Set Start Command:**
   - In Settings → Start Command:
   - `uvicorn demo_main:app --host 0.0.0.0 --port $PORT`
4. **Generate Domain:**
   - Settings → Networking → Generate Domain
5. **Use the new URL** (tell me if it's different)

---

## ✅ After Backend is Fixed

### 1. Test Backend:
```bash
curl https://radtest-production.up.railway.app/health
```

Should return:
```json
{"status":"healthy","service":"RADTest Backend Demo","mode":"demo"}
```

### 2. Redeploy Frontend:

Go to: https://vercel.com/dashboard

- Click "frontend" project
- Click "Deployments" tab
- Click the 3 dots on latest deployment
- Click "Redeploy"

(I already set the environment variable for you!)

### 3. Test Full System:

Visit: https://frontend-eight-rho-17.vercel.app

- Fill out the form
- Submit
- Should work! 🎉

---

## 🆘 Still Not Working?

### Check These:

**In Railway:**
- [ ] Root directory is `backend`
- [ ] Start command is `uvicorn demo_main:app --host 0.0.0.0 --port $PORT`
- [ ] Build succeeded (check logs)
- [ ] Service is running (not stopped)
- [ ] Domain is generated

**Files Deployed:**
- [ ] `demo_main.py` exists
- [ ] `requirements.txt` exists
- [ ] `Procfile` exists (optional)

**Logs Show:**
- Look for "Application startup complete"
- Should see "Uvicorn running on http://0.0.0.0:XXXX"

---

## 🎯 Quick Commands to Help Debug

Run these and tell me the output:

```bash
# Test backend health
curl -v https://radtest-production.up.railway.app/health

# Test backend root
curl https://radtest-production.up.railway.app/

# Test backend docs
curl https://radtest-production.up.railway.app/docs
```

---

## 📋 Correct Railway Configuration

For reference, your Railway service should have:

**Settings:**
```
Name: backend
Root Directory: backend
Start Command: uvicorn demo_main:app --host 0.0.0.0 --port $PORT
```

**Variables:**
```
PORT: (auto-set by Railway)
```

**Files in backend directory:**
- demo_main.py ✅
- requirements.txt ✅
- runtime.txt ✅
- Procfile ✅

---

## 💡 Alternative: Use Different Entry Point

If demo_main.py isn't working, try using the production version:

**Change Start Command to:**
```
pip install -r requirements.txt && uvicorn src.main:app --host 0.0.0.0 --port $PORT
```

But note: This requires API keys to be set.

---

## 🔄 What I Did

✅ **Set Vercel Environment Variable:**
- `NEXT_PUBLIC_API_URL` = `https://radtest-production.up.railway.app`

⏳ **You Need To:**
1. Fix Railway backend (see above)
2. Redeploy Vercel frontend (from dashboard)
3. Test!

---

**Once the backend is fixed and shows {"status":"healthy"}, tell me and I'll verify the full system!**
