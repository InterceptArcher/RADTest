# 🚀 Quick Start Guide - LLM Council Operational

**Status**: ✅ All APIs Configured - System Ready

---

## Verify Configuration

```bash
cd /workspaces/RADTest/backend
python3 verify_config.py
```

Expected: All keys show ✓ configured

---

## Test Locally (Optional)

```bash
# Install dependencies
pip install -r requirements.txt

# Test LLM Council
python3 test_llm_council.py

# Start backend
python3 production_main.py
```

Backend runs on `http://localhost:8000`

---

## Deploy to Production

See [DEPLOYMENT_READY.md](DEPLOYMENT_READY.md) for complete instructions.

### Quick Deploy to Render.com

1. Go to https://render.com/dashboard
2. New → Web Service
3. Connect GitHub repo: RADTest
4. Set root directory: `backend`
5. Build: `pip install -r requirements.txt`
6. Start: `uvicorn production_main:app --host 0.0.0.0 --port $PORT`
7. Add environment variables (see DEPLOYMENT_READY.md)
8. Deploy

---

## Documentation

- [README.md](README.md) - Full project overview
- [DEPLOYMENT_READY.md](DEPLOYMENT_READY.md) - Complete deployment guide
- [LLM_COUNCIL_OPERATIONAL.md](LLM_COUNCIL_OPERATIONAL.md) - Council architecture
- [CONFIGURATION_COMPLETE.md](CONFIGURATION_COMPLETE.md) - What was configured

---

## What's Working

✅ Intelligence gathering (Apollo + PDL)
✅ LLM Council (10-20 agent validation)
✅ Conflict resolution with confidence scores
✅ Complete audit trails
✅ Frontend deployed: https://frontend-eight-rho-17.vercel.app

**Next**: Deploy backend and update frontend URL
