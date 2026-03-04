/**
 * APIResponseDisplay component for showing API return values.
 * Feature 019: Display API Return Values in Debug UI
 */

'use client';

import { useState, useCallback, useMemo } from 'react';
import type { APIResponseData } from '@/types';

interface APIResponseDisplayProps {
  responses: APIResponseData[];
}

type FilterType = 'all' | 'success' | 'errors';
type SortOrder = 'asc' | 'desc';

/**
 * Mask sensitive data in an object.
 */
const maskSensitiveData = (
  data: unknown,
  maskedFields: string[] = []
): unknown => {
  if (typeof data !== 'object' || data === null) {
    return data;
  }

  if (Array.isArray(data)) {
    return data.map((item) => maskSensitiveData(item, maskedFields));
  }

  const masked: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(data)) {
    if (maskedFields.includes(key)) {
      masked[key] = '********';
    } else if (typeof value === 'object' && value !== null) {
      masked[key] = maskSensitiveData(value, maskedFields);
    } else {
      masked[key] = value;
    }
  }
  return masked;
};

/**
 * Get status color class based on HTTP status code.
 */
const getStatusClass = (statusCode: number): string => {
  if (statusCode >= 200 && statusCode < 300) {
    return 'status-success bg-green-100 text-green-800';
  }
  if (statusCode >= 400) {
    return 'status-error bg-red-100 text-red-800';
  }
  return 'bg-yellow-100 text-yellow-800';
};

/**
 * Get method color class.
 */
const getMethodClass = (method: string): string => {
  const methodClasses: Record<string, string> = {
    GET: 'bg-blue-100 text-blue-800',
    POST: 'bg-green-100 text-green-800',
    PUT: 'bg-yellow-100 text-yellow-800',
    DELETE: 'bg-red-100 text-red-800',
    PATCH: 'bg-purple-100 text-purple-800',
  };
  return methodClasses[method] || 'bg-gray-100 text-gray-800';
};

/**
 * Enrichment summary panel for contact enrich API responses.
 * Shows phone enrichment stats and per-contact status in the debug panel.
 */
function EnrichmentSummaryPanel({ response }: { response: APIResponseData }) {
  const isContactEnrich =
    response.apiName?.toLowerCase().includes('contact') &&
    response.apiName?.toLowerCase().includes('enrich');

  if (!isContactEnrich || typeof response.responseBody !== 'object' || response.responseBody === null) {
    return null;
  }

  const body = response.responseBody as Record<string, unknown>;
  const summary = body.enrichment_summary as {
    total_searched?: number; total_enriched?: number; total_unenriched?: number;
  } | undefined;

  if (!summary) return null;

  const contacts = (body.contacts || []) as Array<{
    name?: string; roleType?: string; directPhone?: string; mobilePhone?: string;
    companyPhone?: string; phone?: string; enriched?: boolean;
  }>;

  return (
    <div className="mb-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-4 border border-blue-100">
      <div className="flex items-center space-x-2 mb-3">
        <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
        </svg>
        <h4 className="text-sm font-semibold text-blue-900">Phone Number Enrichment</h4>
      </div>
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-white/60 rounded-md px-3 py-2 text-center">
          <p className="text-lg font-bold text-slate-900">{summary.total_searched ?? 0}</p>
          <p className="text-xs text-slate-500">Searched</p>
        </div>
        <div className="bg-white/60 rounded-md px-3 py-2 text-center">
          <p className="text-lg font-bold text-green-600">{summary.total_enriched ?? 0}</p>
          <p className="text-xs text-slate-500">Got Real Phones</p>
        </div>
        <div className="bg-white/60 rounded-md px-3 py-2 text-center">
          <p className="text-lg font-bold text-amber-600">{summary.total_unenriched ?? 0}</p>
          <p className="text-xs text-slate-500">No Phone Data</p>
        </div>
      </div>
      {contacts.length > 0 && (
        <div className="mt-3 border-t border-blue-200 pt-3">
          <p className="text-xs font-medium text-blue-800 mb-2">Per-Contact Status:</p>
          <div className="space-y-1">
            {contacts.map((contact, idx) => {
              const hasRealPhone = !!(contact.directPhone || contact.mobilePhone ||
                                      contact.companyPhone || contact.phone);
              return (
                <div key={idx} className="flex items-center justify-between text-xs">
                  <span className="text-slate-700 truncate max-w-[180px]">
                    {contact.name} <span className="text-slate-400">({contact.roleType})</span>
                  </span>
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full font-medium ${
                    hasRealPhone
                      ? 'bg-green-100 text-green-700'
                      : contact.enriched === false
                      ? 'bg-amber-100 text-amber-700'
                      : 'bg-slate-100 text-slate-500'
                  }`}>
                    {hasRealPhone ? 'Phone visible' : contact.enriched === false ? 'Not enriched' : 'No phone'}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * APIResponseDisplay shows API responses with sensitive data masking.
 */
export default function APIResponseDisplay({
  responses,
}: APIResponseDisplayProps) {
  const [expandedResponses, setExpandedResponses] = useState<Set<string>>(
    new Set()
  );
  const [filter, setFilter] = useState<FilterType>('all');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');

  const toggleResponse = useCallback((responseId: string) => {
    setExpandedResponses((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(responseId)) {
        newSet.delete(responseId);
      } else {
        newSet.add(responseId);
      }
      return newSet;
    });
  }, []);

  const isExpanded = (responseId: string): boolean =>
    expandedResponses.has(responseId);

  const filteredAndSortedResponses = useMemo((): APIResponseData[] => {
    let filtered: APIResponseData[] = responses;

    // Apply filter
    if (filter === 'success') {
      filtered = responses.filter(
        (r) => r.statusCode >= 200 && r.statusCode < 300
      );
    } else if (filter === 'errors') {
      filtered = responses.filter((r) => r.statusCode >= 400);
    }

    // Apply sort
    return [...filtered].sort((a, b) => {
      const timeA = new Date(a.timestamp).getTime();
      const timeB = new Date(b.timestamp).getTime();
      return sortOrder === 'asc' ? timeA - timeB : timeB - timeA;
    });
  }, [responses, filter, sortOrder]);

  const copyToClipboard = useCallback(async (data: unknown) => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
    }
  }, []);

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">API Responses</h2>

        {responses.length > 0 && (
          <div className="flex gap-2">
            {/* Filter Buttons */}
            <div className="flex rounded-md shadow-sm">
              <button
                onClick={() => setFilter('all')}
                className={`px-3 py-1.5 text-sm font-medium rounded-l-md border ${
                  filter === 'all'
                    ? 'bg-primary-100 text-primary-700 border-primary-300'
                    : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                }`}
              >
                All
              </button>
              <button
                onClick={() => setFilter('success')}
                className={`px-3 py-1.5 text-sm font-medium border-t border-b ${
                  filter === 'success'
                    ? 'bg-green-100 text-green-700 border-green-300'
                    : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                }`}
              >
                Success
              </button>
              <button
                onClick={() => setFilter('errors')}
                className={`px-3 py-1.5 text-sm font-medium rounded-r-md border ${
                  filter === 'errors'
                    ? 'bg-red-100 text-red-700 border-red-300'
                    : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                }`}
              >
                Errors
              </button>
            </div>

            {/* Sort Button */}
            <button
              onClick={() => setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))}
              className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              aria-label="Sort"
            >
              Sort {sortOrder === 'asc' ? '↑' : '↓'}
            </button>
          </div>
        )}
      </div>

      {/* API Responses List */}
      {filteredAndSortedResponses.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <p>No API responses available</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredAndSortedResponses.map((response: APIResponseData) => (
            <div
              key={response.id}
              className="border border-gray-200 rounded-lg overflow-hidden"
            >
              {/* Response Header */}
              <button
                data-testid={`expand-${response.id}`}
                onClick={() => toggleResponse(response.id)}
                className="w-full flex items-center justify-between p-4 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-primary-500"
                aria-expanded={isExpanded(response.id)}
              >
                <div className="flex items-center gap-3">
                  {/* Status Code */}
                  <span
                    data-testid={`status-${response.id}`}
                    className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${getStatusClass(response.statusCode)}`}
                  >
                    {response.statusCode}
                  </span>

                  {/* API Name */}
                  <span className="font-medium text-gray-900">
                    {response.apiName}
                  </span>

                  {/* Sensitive Indicator */}
                  {response.isSensitive && (
                    <span
                      data-testid={`sensitive-${response.id}`}
                      className="px-2 py-0.5 bg-yellow-100 text-yellow-800 text-xs rounded-full"
                      title="Contains sensitive data"
                    >
                      Sensitive
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  {/* Duration */}
                  <span className="text-sm text-gray-500">
                    {response.duration}ms
                  </span>

                  {/* Expand Icon */}
                  <svg
                    className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded(response.id) ? 'rotate-180' : ''}`}
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

              {/* Response Details (Expandable) */}
              {isExpanded(response.id) && (
                <div className="px-4 pb-4 pt-2 bg-gray-50 border-t border-gray-200">
                  {/* Method and URL */}
                  <div className="flex items-center gap-2 mb-4">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-bold ${getMethodClass(response.method)}`}
                    >
                      {response.method}
                    </span>
                    <code className="text-sm text-gray-700 bg-gray-100 px-2 py-1 rounded break-all">
                      {response.url}
                    </code>
                  </div>

                  <div className="mb-4">
                    <h4 className="text-xs font-medium text-gray-500 uppercase mb-2">
                      Response Headers
                    </h4>
                    <div className="bg-gray-100 rounded-md p-3">
                      {Object.keys(response.headers).map((key: string) => (
                        <div key={key} className="text-xs mb-1">
                          <span className="font-medium text-gray-600">
                            {key}:
                          </span>{' '}
                          <span className="text-gray-700">{String(response.headers[key])}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Request Body (if available) */}
                  {response.requestBody !== undefined && response.requestBody !== null && (
                    <div className="mb-4">
                      <h4 className="text-xs font-medium text-gray-500 uppercase mb-2">
                        Request Body
                      </h4>
                      <pre className="bg-gray-100 rounded-md p-3 text-xs text-gray-700 overflow-x-auto">
                        {JSON.stringify(
                          maskSensitiveData(
                            response.requestBody,
                            response.maskedFields
                          ),
                          null,
                          2
                        )}
                      </pre>
                    </div>
                  )}

                  {/* Phone Enrichment Summary (shown for contact enrich responses) */}
                  <EnrichmentSummaryPanel response={response} />

                  {/* Response Body */}
                  <div className="mb-4">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-xs font-medium text-gray-500 uppercase">
                        Response Body
                      </h4>
                      <button
                        onClick={() => copyToClipboard(response.responseBody)}
                        className="text-xs text-primary-600 hover:text-primary-700"
                        aria-label="Copy response"
                      >
                        Copy
                      </button>
                    </div>
                    <pre className="bg-gray-100 rounded-md p-3 text-xs text-gray-700 overflow-x-auto max-h-64">
                      {JSON.stringify(
                        maskSensitiveData(
                          response.responseBody,
                          response.maskedFields
                        ),
                        null,
                        2
                      )}
                    </pre>
                  </div>

                  {/* Timestamp */}
                  <div className="text-xs text-gray-500">
                    Timestamp:{' '}
                    {new Date(response.timestamp).toLocaleString()}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
