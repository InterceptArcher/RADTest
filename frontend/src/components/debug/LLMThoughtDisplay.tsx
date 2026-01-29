/**
 * LLMThoughtDisplay component for showing ChatGPT thought process.
 * Feature 020: Display ChatGPT Thought Process
 */

'use client';

import { useState, useCallback } from 'react';
import type { LLMThoughtProcess, LLMThoughtStep } from '@/types';

interface LLMThoughtDisplayProps {
  thoughtProcesses: LLMThoughtProcess[];
}

/**
 * Format confidence as percentage.
 */
const formatConfidence = (confidence?: number): string => {
  if (confidence === undefined) return 'N/A';
  return `${Math.round(confidence * 100)}%`;
};

/**
 * Get confidence color class.
 */
const getConfidenceClass = (confidence?: number): string => {
  if (confidence === undefined) return 'bg-gray-100 text-gray-700';
  if (confidence >= 0.8) return 'bg-green-100 text-green-700';
  if (confidence >= 0.6) return 'bg-yellow-100 text-yellow-700';
  return 'bg-red-100 text-red-700';
};

/**
 * Tooltip component for complex terms.
 */
const Tooltip = ({
  children,
  content,
}: {
  children: React.ReactNode;
  content: string;
}) => {
  const [isVisible, setIsVisible] = useState(false);

  return (
    <span
      className="relative inline-block cursor-help"
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
      onFocus={() => setIsVisible(true)}
      onBlur={() => setIsVisible(false)}
      tabIndex={0}
    >
      {children}
      {isVisible && (
        <span
          role="tooltip"
          className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 text-xs text-white bg-gray-900 rounded-md shadow-lg z-10 w-48"
        >
          {content}
        </span>
      )}
    </span>
  );
};

/**
 * LLMThoughtDisplay shows LLM decision-making insights.
 */
export default function LLMThoughtDisplay({
  thoughtProcesses,
}: LLMThoughtDisplayProps) {
  const [expandedProcesses, setExpandedProcesses] = useState<Set<string>>(
    new Set()
  );
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());

  const toggleProcess = useCallback((processId: string) => {
    setExpandedProcesses((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(processId)) {
        newSet.delete(processId);
      } else {
        newSet.add(processId);
      }
      return newSet;
    });
  }, []);

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

  const isProcessExpanded = (processId: string): boolean =>
    expandedProcesses.has(processId);

  const isStepExpanded = (stepId: string): boolean => expandedSteps.has(stepId);

  return (
    <section
      role="region"
      aria-label="LLM Thought Process"
      className="bg-white rounded-lg shadow-lg p-6"
    >
      {/* Header */}
      <h2 className="text-2xl font-bold text-gray-900 mb-6">
        LLM Thought Process
      </h2>

      {/* Thought Processes List */}
      {thoughtProcesses.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <p>No LLM thought processes available</p>
        </div>
      ) : (
        <div className="space-y-4">
          {thoughtProcesses.map((process) => (
            <div
              key={process.id}
              className="border border-gray-200 rounded-lg overflow-hidden"
            >
              {/* Process Header */}
              <button
                data-testid={`expand-${process.id}`}
                onClick={() => toggleProcess(process.id)}
                className="w-full flex items-center justify-between p-4 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-primary-500"
                aria-expanded={isProcessExpanded(process.id)}
              >
                <div className="flex items-center gap-3">
                  {/* Task Name */}
                  <span className="font-medium text-gray-900">
                    {process.taskName}
                  </span>

                  {/* Model Badge */}
                  <span className="px-2.5 py-0.5 bg-purple-100 text-purple-800 text-xs rounded-full font-medium">
                    {process.model}
                  </span>
                </div>

                {/* Expand Icon */}
                <svg
                  className={`w-5 h-5 text-gray-400 transition-transform ${isProcessExpanded(process.id) ? 'rotate-180' : ''}`}
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
              </button>

              {/* Process Details (Expandable) */}
              {isProcessExpanded(process.id) && (
                <div className="px-4 pb-4 pt-2 bg-gray-50 border-t border-gray-200">
                  {/* Timestamps */}
                  <div className="flex gap-6 mb-4 text-sm text-gray-600">
                    <div>
                      <span className="font-medium">Started:</span>{' '}
                      {new Date(process.startTime).toLocaleTimeString()}
                    </div>
                    {process.endTime && (
                      <div>
                        <span className="font-medium">Completed:</span>{' '}
                        {new Date(process.endTime).toLocaleTimeString()}
                      </div>
                    )}
                  </div>

                  {/* Steps */}
                  <div className="space-y-3 mb-4">
                    {process.steps.map((step) => (
                      <div
                        key={step.id}
                        className="border border-gray-200 rounded-md bg-white"
                      >
                        {/* Step Header */}
                        <button
                          data-testid={`expand-${step.id}`}
                          onClick={() => toggleStep(step.id)}
                          className="w-full flex items-center justify-between p-3 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-primary-500"
                          aria-expanded={isStepExpanded(step.id)}
                        >
                          <div className="flex items-center gap-3">
                            {/* Step Number */}
                            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-primary-100 text-primary-700 text-xs font-medium">
                              {step.step}
                            </span>
                            <span className="text-sm text-gray-500">
                              Step {step.step}
                            </span>
                            <span className="font-medium text-gray-900">
                              {step.action}
                            </span>
                          </div>

                          <div className="flex items-center gap-3">
                            {/* Confidence */}
                            {step.confidence !== undefined && (
                              <Tooltip content="The model's confidence in this step's conclusion">
                                <span
                                  className={`px-2 py-0.5 rounded text-xs font-medium ${getConfidenceClass(step.confidence)}`}
                                >
                                  <span className="confidence">Confidence:</span>{' '}
                                  {formatConfidence(step.confidence)}
                                </span>
                              </Tooltip>
                            )}

                            {/* Expand Icon */}
                            <svg
                              className={`w-4 h-4 text-gray-400 transition-transform ${isStepExpanded(step.id) ? 'rotate-180' : ''}`}
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
                        {isStepExpanded(step.id) && (
                          <div className="px-3 pb-3 border-t border-gray-100">
                            {/* Reasoning */}
                            <div className="mt-3">
                              <h5 className="text-xs font-medium text-gray-500 uppercase mb-1">
                                Reasoning
                              </h5>
                              <p className="text-sm text-gray-700 bg-gray-50 p-3 rounded-md">
                                {step.reasoning}
                              </p>
                            </div>

                            {/* Input */}
                            {step.input !== undefined && step.input !== null && (
                              <div className="mt-3">
                                <h5 className="text-xs font-medium text-gray-500 uppercase mb-1">
                                  Input
                                </h5>
                                <pre className="text-xs text-gray-700 bg-gray-50 p-3 rounded-md overflow-x-auto">
                                  {JSON.stringify(step.input, null, 2)}
                                </pre>
                              </div>
                            )}

                            {/* Output */}
                            {step.output !== undefined && step.output !== null && (
                              <div className="mt-3">
                                <h5 className="text-xs font-medium text-gray-500 uppercase mb-1">
                                  Output
                                </h5>
                                <pre className="text-xs text-gray-700 bg-gray-50 p-3 rounded-md overflow-x-auto">
                                  {JSON.stringify(step.output, null, 2)}
                                </pre>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  {/* Discrepancies Resolved */}
                  {process.discrepanciesResolved &&
                    process.discrepanciesResolved.length > 0 && (
                      <div className="mb-4">
                        <h4 className="text-xs font-medium text-gray-500 uppercase mb-2">
                          Discrepancies Resolved
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          {process.discrepanciesResolved.map((field, index) => (
                            <span
                              key={index}
                              className="px-2.5 py-1 bg-green-100 text-green-800 text-xs rounded-full"
                            >
                              {field}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                  {/* Final Decision */}
                  <div
                    data-testid={`final-decision-${process.id}`}
                    className="p-4 bg-primary-50 border border-primary-200 rounded-md"
                  >
                    <h4 className="text-sm font-medium text-primary-900 mb-2">
                      Final Decision
                    </h4>
                    <p className="text-sm text-primary-800">
                      {process.finalDecision}
                    </p>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
