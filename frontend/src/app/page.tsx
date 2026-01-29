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

      // Poll for job status until complete
      pollJobStatus(response.job_id);

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
   * Poll job status until complete or failed.
   */
  const pollJobStatus = async (jobId: string) => {
    const maxAttempts = 60; // Max 2 minutes (60 * 2 seconds)
    let attempts = 0;

    while (attempts < maxAttempts) {
      try {
        const jobStatus = await apiClient.checkJobStatus(jobId);

        // Update progress from actual backend status
        if (jobStatus.progress !== undefined) {
          setProgress(jobStatus.progress);
        }
        if (jobStatus.current_step) {
          setCurrentStep(jobStatus.current_step);
        }

        if (jobStatus.status === 'completed' && jobStatus.result) {
          setResult(jobStatus.result);
          setState('results');
          return;
        }

        if (jobStatus.status === 'failed') {
          throw new Error(jobStatus.current_step || 'Job processing failed');
        }

        // Wait 2 seconds before next poll
        await new Promise((resolve) => setTimeout(resolve, 2000));
        attempts++;

      } catch (err) {
        setState('error');
        setError(
          err instanceof Error
            ? err.message
            : 'Failed to retrieve results. Please try again.'
        );
        return;
      }
    }

    // Timeout after max attempts
    setState('error');
    setError('Request timed out. Please try again.');
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
            <ResultsDisplay result={result} onReset={handleReset} jobId={jobId ?? undefined} />
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
