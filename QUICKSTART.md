# RADTest Quick Start Guide

This guide will help you get the RADTest application running locally.

## Prerequisites

- Node.js 18+ (for frontend)
- Python 3.11+ (for backend)
- npm or yarn
- pip

## Step 1: Clone and Setup

```bash
# Navigate to project
cd /workspaces/RADTest
```

## Step 2: Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Create environment file
cp .env.example .env.local

# Edit .env.local
# Set NEXT_PUBLIC_API_URL=http://localhost:8000
nano .env.local

# Start development server
npm run dev
```

Frontend will be available at: http://localhost:3000

## Step 3: Backend Setup (Separate Terminal)

```bash
# Navigate to backend
cd backend

# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env

# Edit .env and set all required variables
# IMPORTANT: These must be provided for the backend to work
nano .env
```

**Required Environment Variables for Backend**:
```bash
RAILWAY_WORKER_URL=http://localhost:8001  # Or actual Railway URL
RAILWAY_API_TOKEN=your-token-here
RAILWAY_PROJECT_ID=your-project-id
RAILWAY_ENVIRONMENT_ID=your-env-id
RAILWAY_SERVICE_ID=your-service-id
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
APOLLO_API_KEY=your-apollo-key
PDL_API_KEY=your-pdl-key
OPENAI_API_KEY=your-openai-key
GAMMA_API_KEY=your-gamma-key
```

```bash
# Start FastAPI server
uvicorn src.main:app --reload
```

Backend API will be available at: http://localhost:8000

## Step 4: Test the Application

1. Open http://localhost:3000 in your browser
2. Fill in the company profile form:
   - Company Name: e.g., "Acme Corporation"
   - Domain: e.g., "acme.com"
   - Industry: e.g., "Technology" (optional)
   - Your Email: e.g., "you@example.com"
3. Click "Generate Profile"
4. Watch the processing progress
5. View the results and slideshow link

## Running Tests

### Frontend Tests
```bash
cd frontend
npm test
```

### Backend Tests
```bash
cd backend
pytest
```

## Common Issues

### Frontend can't connect to backend
- Ensure backend is running on port 8000
- Check `NEXT_PUBLIC_API_URL` in `.env.local`
- Verify no CORS issues (FastAPI should allow localhost)

### Backend fails to start
- Check that all environment variables are set
- Verify Python version (3.11+)
- Ensure all dependencies are installed

### Missing API keys
- You need actual API keys for:
  - Railway (for worker deployment)
  - Supabase (for database)
  - Apollo.io (for company data)
  - PeopleDataLabs (for company data)
  - OpenAI (for LLM validation)
  - Gamma (for slideshow generation)
- For development, you can mock these services

## Development Workflow

1. **Make changes to frontend**:
   - Next.js has hot reload enabled
   - Changes appear immediately in browser

2. **Make changes to backend**:
   - FastAPI auto-reloads with `--reload` flag
   - API changes take effect immediately

3. **Run tests after changes**:
   ```bash
   # Frontend
   cd frontend && npm test

   # Backend
   cd backend && pytest
   ```

## Next Steps

- Read the full README.md for architecture details
- Check individual component documentation
- Review the feature specifications in docs/
- Deploy to production (Vercel + Railway)

## Getting Help

- Check the README.md for detailed information
- Review CLAUDE.md for engineering standards
- Check component tests for usage examples
- Review API documentation at http://localhost:8000/docs

## Production Deployment

See the main README.md for full deployment instructions to:
- **Frontend**: Vercel
- **Backend**: Railway
- **Database**: Supabase

Each platform requires setting the appropriate environment variables through their respective dashboards.
