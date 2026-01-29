/**
 * DebugPanel component for process inspection.
 * Feature 018: Debugging UI for Process Inspection
 */

'use client';

import { useState, useCallback } from 'react';
import type { ProcessStep } from '@/types';

interface DebugPanelProps {
  steps: ProcessStep[];
}

/**
 * Format timestamp for display.
 */
const formatTimestamp = (timestamp: string): string => {
  return new Date(timestamp).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    fractionalSecondDigits: 3,
  });
};

/**
 * Get status color class.
 */
const getStatusClass = (status: ProcessStep['status']): string => {
  const statusClasses = {
    pending: 'bg-gray-200 text-gray-700',
    in_progress: 'bg-blue-200 text-blue-700 animate-pulse',
    completed: 'bg-green-200 text-green-700',
    failed: 'bg-red-200 text-red-700',
  };
  return statusClasses[status] || statusClasses.pending;
};

/**
 * DebugPanel displays process steps with expandable details.
 */
export default function DebugPanel({ steps }: DebugPanelProps) {
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());

  const toggleStep = useCallback((stepId: string) => {
    setExpandedSteps((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(stepId)) {
        newSet.delete(stepId);
      } else {
        newSet.add(stepId);
      }
      return newSet;
    });
  }, []);

  const expandAll = useCallback(() => {
    setExpandedSteps(new Set(steps.map((s) => s.id)));
  }, [steps]);

  const collapseAll = useCallback(() => {
    setExpandedSteps(new Set());
  }, []);

  const isExpanded = (stepId: string): boolean => expandedSteps.has(stepId);
  const allExpanded = steps.length > 0 && expandedSteps.size === steps.length;

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Debug Mode</h2>
          <p className="text-sm text-gray-600 mt-1">Process Inspection</p>
        </div>
        {steps.length > 0 && (
          <div className="flex gap-2">
            {allExpanded ? (
              <button
                onClick={collapseAll}
                className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
              >
                Collapse All
              </button>
            ) : (
              <button
                onClick={expandAll}
                className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
              >
                Expand All
              </button>
            )}
          </div>
        )}
      </div>

      {/* Process Steps */}
      {steps.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <p>No process steps available</p>
        </div>
      ) : (
        <div className="space-y-3">
          {steps.map((step, index) => (
            <div
              key={step.id}
              className="border border-gray-200 rounded-lg overflow-hidden"
            >
              {/* Step Header */}
              <button
                data-testid={`expand-${step.id}`}
                onClick={() => toggleStep(step.id)}
                className="w-full flex items-center justify-between p-4 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-primary-500"
                aria-expanded={isExpanded(step.id)}
              >
                <div className="flex items-center gap-4">
                  {/* Step Number */}
                  <span className="flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 text-gray-700 font-medium text-sm">
                    {index + 1}
                  </span>

                  {/* Step Name */}
                  <span className="font-medium text-gray-900">{step.name}</span>

                  {/* Status Badge */}
                  <span
                    data-testid={`status-${step.id}`}
                    className={`status-${step.status} px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusClass(step.status)}`}
                  >
                    {step.status.replace('_', ' ')}
                  </span>
                </div>

                {/* Duration (if available) */}
                <div className="flex items-center gap-3">
                  {step.duration && (
                    <span className="text-sm text-gray-500">
                      {step.duration}ms
                    </span>
                  )}

                  {/* Expand Icon */}
                  <svg
                    className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded(step.id) ? 'rotate-180' : ''}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                </div>
              </button>

              {/* Step Details (Expandable) */}
              {isExpanded(step.id) && (
                <div className="px-4 pb-4 pt-2 bg-gray-50 border-t border-gray-200">
                  {/* Description */}
                  <p className="text-gray-700 mb-4">{step.description}</p>

                  {/* Timing Information */}
                  {(step.startTime || step.endTime) && (
                    <div className="grid grid-cols-2 gap-4 mb-4">
                      {step.startTime && (
                        <div>
                          <span className="text-xs font-medium text-gray-500 uppercase">
                            Start:
                          </span>
                          <p className="text-sm text-gray-700">
                            {formatTimestamp(step.startTime)}
                          </p>
                        </div>
                      )}
                      {step.endTime && (
                        <div>
                          <span className="text-xs font-medium text-gray-500 uppercase">
                            End:
                          </span>
                          <p className="text-sm text-gray-700">
                            {formatTimestamp(step.endTime)}
                          </p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Metadata */}
                  {step.metadata && Object.keys(step.metadata).length > 0 && (
                    <div>
                      <span className="text-xs font-medium text-gray-500 uppercase">
                        Metadata:
                      </span>
                      <pre className="mt-1 p-3 bg-gray-100 rounded-md text-xs text-gray-700 overflow-x-auto">
                        {JSON.stringify(step.metadata, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
