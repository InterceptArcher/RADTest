/**
 * Debug Mode Page.
 * Features 018-021: Debug UI for Process Inspection
 */

'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import {
  DebugPanel,
  APIResponseDisplay,
  LLMThoughtDisplay,
  ProcessFlowVisualization,
} from '@/components/debug';
import LoadingSpinner from '@/components/LoadingSpinner';
import { debugApiClient } from '@/lib/debugApi';
import type { DebugData } from '@/types';

type TabType = 'process' | 'api' | 'llm' | 'flow';

/**
 * Tab button component.
 */
const TabButton = ({
  tab,
  activeTab,
  onClick,
  children,
}: {
  tab: TabType;
  activeTab: TabType;
  onClick: (tab: TabType) => void;
  children: React.ReactNode;
}) => (
  <button
    onClick={() => onClick(tab)}
    className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
      activeTab === tab
        ? 'bg-white text-primary-700 border-t border-l border-r border-gray-200'
        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
    }`}
    role="tab"
    aria-selected={activeTab === tab}
    aria-controls={`${tab}-panel`}
  >
    {children}
  </button>
);

/**
 * Debug Mode content component.
 */
function DebugModeContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const jobId = searchParams.get('jobId');

  const [debugData, setDebugData] = useState<DebugData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('process');

  useEffect(() => {
    if (!jobId) {
      setError('No job ID provided. Please access Debug Mode from a completed job.');
      setLoading(false);
      return;
    }

    const fetchDebugData = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await debugApiClient.getDebugData(jobId);
        setDebugData(data);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : 'Failed to load debug data. Please try again.'
        );
      } finally {
        setLoading(false);
      }
    };

    fetchDebugData();
  }, [jobId]);

  const handleBack = () => {
    router.back();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <LoadingSpinner message="Loading debug data..." progress={50} />
      </div>
    );
  }

  if (error) {
    return (
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
          Unable to Load Debug Data
        </h2>
        <p className="text-gray-600 mb-6">{error}</p>
        <button
          onClick={handleBack}
          className="px-6 py-3 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
        >
          Go Back
        </button>
      </div>
    );
  }

  if (!debugData) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <button
            onClick={handleBack}
            className="flex items-center text-gray-600 hover:text-gray-900 mb-2"
          >
            <svg
              className="w-5 h-5 mr-1"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
            Back to Results
          </button>
          <h1 className="text-3xl font-bold text-gray-900">
            Debug Mode: {debugData.companyName}
          </h1>
          <p className="text-gray-600 mt-1">
            Job ID: {debugData.jobId} | Domain: {debugData.domain}
          </p>
        </div>

        {/* Status Badge */}
        <span
          className={`px-4 py-2 rounded-full text-sm font-medium ${
            debugData.status === 'completed'
              ? 'bg-green-100 text-green-800'
              : debugData.status === 'failed'
                ? 'bg-red-100 text-red-800'
                : 'bg-blue-100 text-blue-800'
          }`}
        >
          {debugData.status.charAt(0).toUpperCase() + debugData.status.slice(1)}
        </span>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-1" role="tablist">
          <TabButton tab="process" activeTab={activeTab} onClick={setActiveTab}>
            Process Steps ({debugData.processSteps.length})
          </TabButton>
          <TabButton tab="api" activeTab={activeTab} onClick={setActiveTab}>
            API Responses ({debugData.apiResponses.length})
          </TabButton>
          <TabButton tab="llm" activeTab={activeTab} onClick={setActiveTab}>
            LLM Insights ({debugData.llmThoughtProcesses.length})
          </TabButton>
          <TabButton tab="flow" activeTab={activeTab} onClick={setActiveTab}>
            Process Flow
          </TabButton>
        </nav>
      </div>

      {/* Tab Panels */}
      <div className="mt-4">
        {activeTab === 'process' && (
          <div id="process-panel" role="tabpanel">
            <DebugPanel steps={debugData.processSteps} />
          </div>
        )}

        {activeTab === 'api' && (
          <div id="api-panel" role="tabpanel">
            <APIResponseDisplay responses={debugData.apiResponses} />
          </div>
        )}

        {activeTab === 'llm' && (
          <div id="llm-panel" role="tabpanel">
            <LLMThoughtDisplay
              thoughtProcesses={debugData.llmThoughtProcesses}
            />
          </div>
        )}

        {activeTab === 'flow' && (
          <div id="flow-panel" role="tabpanel">
            <ProcessFlowVisualization flow={debugData.processFlow} />
          </div>
        )}
      </div>

      {/* Timestamps */}
      <div className="text-sm text-gray-500 text-center pt-4 border-t border-gray-200">
        Created: {new Date(debugData.createdAt).toLocaleString()}
        {debugData.completedAt && (
          <> | Completed: {new Date(debugData.completedAt).toLocaleString()}</>
        )}
      </div>
    </div>
  );
}

/**
 * Debug Mode Page with Suspense boundary.
 */
export default function DebugModePage() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <Suspense
          fallback={
            <div className="flex items-center justify-center min-h-[60vh]">
              <LoadingSpinner message="Loading..." progress={0} />
            </div>
          }
        >
          <DebugModeContent />
        </Suspense>
      </div>
    </main>
  );
}
