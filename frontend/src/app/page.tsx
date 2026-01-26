/**
 * Main application page.
 * Handles company profile request workflow.
 */

'use client';

import { useState, useEffect } from 'react';
import ProfileRequestForm from '@/components/ProfileRequestForm';
import ResultsDisplay from '@/components/ResultsDisplay';
import LoadingSpinner from '@/components/LoadingSpinner';
import { apiClient } from '@/lib/api';
import type {
  CompanyProfileRequest,
  ProfileResult,
} from '@/types';

type AppState = 'form' | 'loading' | 'results' | 'error';

export default function Home() {
  const [state, setState] = useState<AppState>('form');
  const [result, setResult] = useState<ProfileResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [progress, setProgress] = useState<number>(0);
  const [currentStep, setCurrentStep] = useState<string>('Initializing...');

  /**
   * Handle form submission.
   */
  const handleSubmit = async (data: CompanyProfileRequest) => {
    try {
      setState('loading');
      setError(null);
      setProgress(10);
      setCurrentStep('Submitting request...');

      // Submit profile request
      const response = await apiClient.submitProfileRequest(data);
      setJobId(response.job_id);
      setProgress(20);
      setCurrentStep('Request submitted, processing...');

      // In a real implementation, you would poll for job status
      // For now, we'll simulate the process
      simulateProcessing(response.job_id);

    } catch (err) {
      setState('error');
      setError(
        err instanceof Error
          ? err.message
          : 'An unexpected error occurred. Please try again.'
      );
    }
  };

  /**
   * Simulate processing (replace with actual polling in production).
   */
  const simulateProcessing = async (jobId: string) => {
    // Simulate progress updates
    const steps = [
      { progress: 30, step: 'Gathering intelligence from Apollo.io...' },
      { progress: 40, step: 'Gathering intelligence from PeopleDataLabs...' },
      { progress: 50, step: 'Storing raw data...' },
      { progress: 60, step: 'Validating data with LLM agents...' },
      { progress: 70, step: 'Resolving conflicts with LLM council...' },
      { progress: 80, step: 'Finalizing validated data...' },
      { progress: 90, step: 'Generating slideshow...' },
      { progress: 100, step: 'Complete!' },
    ];

    for (const { progress: prog, step } of steps) {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      setProgress(prog);
      setCurrentStep(step);
    }

    // Simulate final result
    // In production, this would come from actual API polling
    setResult({
      success: true,
      company_name: 'Acme Corporation',
      domain: 'acme.com',
      slideshow_url: 'https://gamma.app/docs/example-slideshow',
      confidence_score: 0.85,
      validated_data: {
        company_name: 'Acme Corporation',
        domain: 'acme.com',
        industry: 'Technology',
        employee_count: '1000-5000',
        revenue: '$100M - $500M',
        headquarters: 'San Francisco, CA',
        founded_year: 2010,
        ceo: 'John Doe',
        technology: ['Python', 'React', 'PostgreSQL'],
        target_market: 'Enterprise',
        geographic_reach: 'Global',
        contacts: {
          website: 'acme.com',
          linkedin: 'https://linkedin.com/company/acme',
          email: 'contact@acme.com',
        },
      },
    });

    setState('results');
  };

  /**
   * Reset to form state.
   */
  const handleReset = () => {
    setState('form');
    setResult(null);
    setError(null);
    setJobId(null);
    setProgress(0);
    setCurrentStep('Initializing...');
  };

  /**
   * Check backend health on mount.
   */
  useEffect(() => {
    const checkHealth = async () => {
      const isHealthy = await apiClient.checkHealth();
      if (!isHealthy) {
        console.warn('Backend API is not reachable');
      }
    };

    checkHealth();
  }, []);

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <div className="container mx-auto px-4 py-12 max-w-4xl">
        {/* Header */}
        <header className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
            Company Intelligence Profile Generator
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Generate comprehensive company profiles powered by AI. We gather data
            from multiple sources, validate with LLM agents, and create
            professional slideshows automatically.
          </p>
        </header>

        {/* Main Content */}
        <div className="bg-white rounded-xl shadow-lg p-8">
          {state === 'form' && (
            <ProfileRequestForm
              onSubmit={handleSubmit}
              isLoading={false}
              error={error}
            />
          )}

          {state === 'loading' && (
            <LoadingSpinner message={currentStep} progress={progress} />
          )}

          {state === 'results' && result && (
            <ResultsDisplay result={result} onReset={handleReset} />
          )}

          {state === 'error' && (
            <div className="text-center py-12">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-full mb-4">
                <svg
                  className="w-8 h-8 text-red-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Something went wrong
              </h2>
              <p className="text-gray-600 mb-6">{error}</p>
              <button
                onClick={handleReset}
                className="px-6 py-3 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
              >
                Try Again
              </button>
            </div>
          )}
        </div>

        {/* Footer */}
        <footer className="mt-12 text-center text-sm text-gray-500">
          <p>
            Powered by Apollo.io, PeopleDataLabs, OpenAI, and Gamma API
          </p>
          <p className="mt-2">
            Data validated with multi-agent LLM council for maximum accuracy
          </p>
        </footer>
      </div>
    </main>
  );
}
