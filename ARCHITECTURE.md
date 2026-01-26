# RADTest System Architecture

## Overview

RADTest is a full-stack application for generating AI-powered company intelligence profiles with automated slideshow creation.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                            USER INTERFACE                            │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Next.js Frontend                          │   │
│  │                    (Deployed on Vercel)                      │   │
│  │                                                               │   │
│  │  • ProfileRequestForm - Collects company data                │   │
│  │  • ResultsDisplay - Shows validated profiles                 │   │
│  │  • LoadingSpinner - Progress tracking                        │   │
│  │  • API Client - Backend communication                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTPS
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        BACKEND API LAYER                             │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    FastAPI Backend                           │   │
│  │                  (Deployed on Railway)                       │   │
│  │                                                               │   │
│  │  • /profile-request - Accepts company requests               │   │
│  │  • /health - Health check endpoint                           │   │
│  │  • Railway GraphQL Client - Trigger workers                  │   │
│  │  • Pydantic Models - Request/response validation             │   │
│  └─────────────────────────────────────────────────────────────┘   │
└───────────────┬─────────────────────────┬───────────────────────────┘
                │                         │
                │ GraphQL Mutation        │ Job Status
                │                         │
                ▼                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      WORKER ORCHESTRATION                            │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Ephemeral Railway Worker                        │   │
│  │              (Containerized Python)                          │   │
│  │                                                               │   │
│  │  ┌──────────────────────────────────────────────────┐       │   │
│  │  │  1. Intelligence Gatherer                         │       │   │
│  │  │     • Parallel async requests                     │       │   │
│  │  │     • Circuit breakers                            │       │   │
│  │  │     • Retry with exponential backoff              │       │   │
│  │  └──────────────────────────────────────────────────┘       │   │
│  │                          │                                    │   │
│  │                          ▼                                    │   │
│  │  ┌──────────────────────────────────────────────────┐       │   │
│  │  │  2. Supabase Injector                            │       │   │
│  │  │     • Raw data → raw-data table                  │       │   │
│  │  │     • Batch insert operations                    │       │   │
│  │  └──────────────────────────────────────────────────┘       │   │
│  │                          │                                    │   │
│  │                          ▼                                    │   │
│  │  ┌──────────────────────────────────────────────────┐       │   │
│  │  │  3. LLM Validator + Council                      │       │   │
│  │  │     • 10-20 LLM agents evaluate data             │       │   │
│  │  │     • Revolver consolidates signals              │       │   │
│  │  │     • Resolution rules applied                   │       │   │
│  │  └──────────────────────────────────────────────────┘       │   │
│  │                          │                                    │   │
│  │                          ▼                                    │   │
│  │  ┌──────────────────────────────────────────────────┐       │   │
│  │  │  4. Supabase Finalizer                           │       │   │
│  │  │     • Validated data → finalize-data table       │       │   │
│  │  │     • Confidence scores stored                   │       │   │
│  │  └──────────────────────────────────────────────────┘       │   │
│  │                          │                                    │   │
│  │                          ▼                                    │   │
│  │  ┌──────────────────────────────────────────────────┐       │   │
│  │  │  5. Gamma Slideshow Creator                      │       │   │
│  │  │     • Markdown template generation               │       │   │
│  │  │     • Professional slideshow via API             │       │   │
│  │  └──────────────────────────────────────────────────┘       │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  Apollo.io   │      │ PeopleData   │      │   OpenAI     │
│              │      │    Labs      │      │   GPT-4      │
│  Company     │      │  Company     │      │   LLM for    │
│  Data        │      │  Analytics   │      │  Validation  │
└──────────────┘      └──────────────┘      └──────────────┘

        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  Supabase    │      │   Gamma API  │      │   Railway    │
│  PostgreSQL  │      │  Slideshow   │      │   Platform   │
│              │      │  Generation  │      │              │
│  Database    │      │              │      │  Container   │
│  Storage     │      │              │      │  Hosting     │
└──────────────┘      └──────────────┘      └──────────────┘
```

## Data Flow

### 1. Request Phase
```
User → Frontend Form → Validation → API Client → FastAPI Backend
```

### 2. Orchestration Phase
```
FastAPI → Railway GraphQL API → Ephemeral Worker Provisioned
```

### 3. Intelligence Gathering Phase
```
Worker → [Apollo.io + PeopleDataLabs] (Parallel) → Raw Data Compiled
```

### 4. Storage Phase
```
Raw Data → Supabase raw-data table
```

### 5. Validation Phase
```
Raw Data → LLM Council (10-20 agents) → Signals Generated
         → Revolver Agent → Resolution Rules → Winner Selected
```

### 6. Finalization Phase
```
Validated Data → Supabase finalize-data table
              → Confidence Score Calculated
```

### 7. Slideshow Generation Phase
```
Finalized Data → Markdown Template → Gamma API → Slideshow URL
```

### 8. Response Phase
```
Results → Frontend → User Interface Display
```

## Component Responsibilities

### Frontend (Next.js)
- **Purpose**: User interface and interaction
- **Key Features**:
  - Form validation and sanitization
  - Real-time error feedback
  - Progress tracking
  - Results visualization
- **Technology**: TypeScript, React, Tailwind CSS

### Backend API (FastAPI)
- **Purpose**: Request handling and orchestration
- **Key Features**:
  - REST API endpoints
  - Request validation with Pydantic
  - Railway worker triggering
  - Error handling
- **Technology**: Python, FastAPI, httpx

### Worker (Ephemeral Container)
- **Purpose**: Data processing pipeline
- **Key Features**:
  - Parallel API calls
  - LLM-based validation
  - Data storage
  - Slideshow generation
- **Technology**: Python, asyncio, Docker

### Intelligence Gatherer
- **Purpose**: Collect data from multiple sources
- **Key Features**:
  - Async parallel execution
  - Circuit breaker pattern
  - Retry with exponential backoff
  - Rate limit handling
- **APIs**: Apollo.io, PeopleDataLabs

### LLM Council & Revolver
- **Purpose**: Multi-agent data validation
- **Key Features**:
  - 10-20 independent LLM agents
  - Signal-based evaluation
  - Weighted scoring
  - Transparent audit trail
- **Technology**: OpenAI GPT-4

### Supabase Integration
- **Purpose**: Data persistence
- **Tables**:
  - `raw-data`: Initial API responses
  - `staging-normalized`: Normalized for validation
  - `finalize-data`: Validated results
- **Technology**: PostgreSQL, Supabase client

### Gamma Integration
- **Purpose**: Slideshow generation
- **Key Features**:
  - Markdown-based templates
  - Professional themes
  - Auto-layout
  - External link generation
- **Technology**: Gamma API

## Security Architecture

### Frontend Security
- No secrets in client code
- Environment variables for API URLs only
- Input sanitization and validation
- HTTPS enforcement

### Backend Security
- All secrets via environment variables
- Token-based authentication for Railway
- API key management for external services
- Request size limiting
- Rate limiting (planned)

### Worker Security
- Isolated container execution
- Environment-injected secrets
- No persistent storage of credentials
- Automatic cleanup after completion

## Scalability Considerations

### Horizontal Scaling
- **Frontend**: Vercel auto-scales globally
- **Backend**: Railway supports multiple instances
- **Workers**: Ephemeral, scale on-demand

### Performance Optimizations
- Async/await throughout
- Parallel API calls
- Batch database operations
- Circuit breakers prevent cascade failures

### Cost Optimization
- Workers spin down after completion
- Pay only for active processing time
- Efficient database queries
- Cached responses (planned)

## Error Handling Strategy

### Frontend
- Form validation prevents bad requests
- User-friendly error messages
- Retry mechanism for network failures
- Loading states for UX

### Backend
- Pydantic validation for requests
- HTTP status codes for different errors
- Detailed error logging
- Graceful degradation

### Worker
- Try-catch blocks for each step
- Partial success handling
- Error state storage in database
- Notification on failure (planned)

## Monitoring & Observability

### Logs
- Frontend: Browser console + Vercel logs
- Backend: Railway logs with timestamps
- Worker: Structured logging to stdout

### Metrics (Planned)
- Request success rate
- Processing time
- Confidence score distribution
- API failure rates

### Alerting (Planned)
- Worker failures
- API rate limit hits
- Low confidence scores
- Database connection issues

## Deployment Architecture

### Vercel (Frontend)
- CDN distribution
- Automatic HTTPS
- Preview deployments
- Environment variables per deployment

### Railway (Backend + Workers)
- Container-based deployment
- Environment variable injection
- GraphQL API for orchestration
- Automatic scaling

### Supabase (Database)
- Managed PostgreSQL
- Automatic backups
- Row-level security
- Real-time capabilities (unused currently)

## Technology Justification

### Why Next.js?
- React-based, modern
- TypeScript support
- Excellent developer experience
- Vercel deployment synergy

### Why FastAPI?
- Python ecosystem for ML/AI
- Async support
- Auto-generated API docs
- Type safety with Pydantic

### Why Railway?
- Ephemeral workers
- GraphQL API for control
- Cost-effective scaling
- Simple deployment

### Why Supabase?
- PostgreSQL reliability
- Excellent client libraries
- Real-time future potential
- Row-level security

### Why OpenAI GPT-4?
- Best-in-class reasoning
- Multi-agent patterns
- Reliable API
- Structured outputs

### Why Gamma?
- Professional slideshow output
- API-first design
- Markdown input simplicity
- Customization options

## Future Enhancements

1. **Real-time Updates**: WebSocket for live progress
2. **Caching Layer**: Redis for frequently requested companies
3. **Advanced Analytics**: Dashboard for insights
4. **Web Scraping**: Firecrawl for NULL data fallback
5. **Batch Processing**: Multiple companies at once
6. **Custom Templates**: User-defined slideshow themes
7. **Export Formats**: PDF, PowerPoint, JSON downloads
8. **Approval Workflow**: Human-in-the-loop for low confidence
9. **Webhooks**: Notify external systems on completion
10. **Rate Limiting**: Protect APIs from abuse
