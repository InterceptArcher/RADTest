# RADTest Frontend

Next.js-based frontend for the RADTest company intelligence platform.

## Features

- Company profile request form with validation
- Real-time processing status updates
- Results display with confidence scores
- Professional slideshow links
- Responsive design with Tailwind CSS
- TypeScript for type safety
- Comprehensive test coverage

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **HTTP Client**: Axios
- **Testing**: Jest + React Testing Library
- **Deployment**: Vercel

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.example .env.local

# Edit .env.local and set NEXT_PUBLIC_API_URL
# NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Development

```bash
# Run development server
npm run dev

# Open http://localhost:3000
```

### Testing

```bash
# Run tests
npm test

# Run tests in watch mode
npm run test:watch
```

### Building for Production

```bash
# Build production bundle
npm run build

# Start production server
npm start
```

## Environment Variables

All environment variables must be provided via `.env.local` (local development) or Vercel dashboard (production).

### Required Variables

```bash
NEXT_PUBLIC_API_URL=<backend-api-url>
```

**IMPORTANT**: Never commit secrets or actual environment variable values to git. The `.env.example` file shows the required structure only.

## Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx          # Root layout
│   │   ├── page.tsx            # Home page
│   │   └── globals.css         # Global styles
│   ├── components/
│   │   ├── ProfileRequestForm.tsx
│   │   ├── ResultsDisplay.tsx
│   │   ├── LoadingSpinner.tsx
│   │   └── __tests__/
│   ├── lib/
│   │   ├── api.ts              # API client
│   │   ├── validation.ts       # Form validation
│   │   └── __tests__/
│   └── types/
│       └── index.ts            # TypeScript types
├── public/                     # Static assets
├── package.json
├── tsconfig.json
├── tailwind.config.js
├── next.config.js
└── jest.config.js
```

## Component Overview

### ProfileRequestForm
- Collects company information
- Client-side validation with real-time feedback
- Sanitizes domain input
- Handles form submission

### ResultsDisplay
- Displays validated company data
- Shows confidence scores
- Provides slideshow link
- Formatted company information sections

### LoadingSpinner
- Shows processing status
- Progress bar with percentage
- Current processing step

## API Integration

The frontend communicates with the FastAPI backend via the `APIClient` class:

```typescript
import { apiClient } from '@/lib/api';

// Submit profile request
const response = await apiClient.submitProfileRequest({
  company_name: 'Acme Corp',
  domain: 'acme.com',
  industry: 'Technology',
  requested_by: 'user@example.com',
});

// Check job status
const status = await apiClient.checkJobStatus(response.job_id);

// Check backend health
const isHealthy = await apiClient.checkHealth();
```

## Form Validation

Validation rules implemented:

- **Company Name**: Required, 1-500 characters
- **Domain**: Required, valid domain format, 1-255 characters
- **Industry**: Optional, max 200 characters
- **Email**: Required, valid email format

Domain sanitization automatically:
- Removes protocols (http://, https://)
- Removes www prefix
- Removes paths and query strings
- Converts to lowercase
- Trims whitespace

## Testing

Tests cover:
- Form validation logic
- API client methods
- Component rendering
- User interactions
- Error handling
- Loading states

Run tests with:
```bash
npm test
```

## Deployment to Vercel

### Via Vercel CLI

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Production deployment
vercel --prod
```

### Via Vercel Dashboard

1. Connect your GitHub repository
2. Set environment variables in Settings
3. Deploy automatically on push to main

### Environment Variables in Vercel

Set in Vercel Dashboard → Settings → Environment Variables:

- `NEXT_PUBLIC_API_URL`: Backend API URL (e.g., https://your-backend.railway.app)

## Security

- No secrets in code
- Environment variables for configuration
- Input sanitization and validation
- HTTPS enforcement in production
- No inline JavaScript
- Content Security Policy ready

## Accessibility

- Semantic HTML
- ARIA labels and descriptions
- Keyboard navigation support
- Focus management
- Error announcements
- Color contrast compliance

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers

## License

Proprietary - Intercept
