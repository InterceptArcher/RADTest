/**
 * Results display component.
 * Shows company profile data and slideshow link.
 */

'use client';

import type { ProfileResult } from '@/types';

interface ResultsDisplayProps {
  result: ProfileResult;
  onReset: () => void;
}

export default function ResultsDisplay({
  result,
  onReset,
}: ResultsDisplayProps) {
  const {
    company_name,
    domain,
    slideshow_url,
    confidence_score,
    validated_data,
  } = result;

  /**
   * Format confidence score as percentage.
   */
  const formatConfidence = (score: number): string => {
    return `${(score * 100).toFixed(1)}%`;
  };

  /**
   * Get confidence score color class.
   */
  const getConfidenceColor = (score: number): string => {
    if (score >= 0.8) return 'text-green-600 bg-green-50';
    if (score >= 0.6) return 'text-yellow-600 bg-yellow-50';
    return 'text-red-600 bg-red-50';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">
            {company_name}
          </h2>
          <p className="text-gray-600 mt-1">{domain}</p>
        </div>
        <button
          onClick={onReset}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          New Request
        </button>
      </div>

      {/* Confidence Score */}
      <div className={`p-4 rounded-lg ${getConfidenceColor(confidence_score)}`}>
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">Data Confidence Score</span>
          <span className="text-lg font-bold">
            {formatConfidence(confidence_score)}
          </span>
        </div>
      </div>

      {/* Slideshow Link */}
      {slideshow_url && (
        <div className="p-6 bg-primary-50 border border-primary-200 rounded-lg">
          <h3 className="text-lg font-semibold text-primary-900 mb-3">
            Slideshow Generated
          </h3>
          <a
            href={slideshow_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center px-6 py-3 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 transition-colors"
          >
            <svg
              className="w-5 h-5 mr-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
              />
            </svg>
            View Slideshow
          </a>
          <p className="text-xs text-primary-700 mt-2">
            Opens in new tab
          </p>
        </div>
      )}

      {/* Company Data */}
      {validated_data && (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">
              Company Information
            </h3>
          </div>
          <div className="p-6">
            <dl className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Industry */}
              {validated_data.industry && (
                <div>
                  <dt className="text-sm font-medium text-gray-500 mb-1">
                    Industry
                  </dt>
                  <dd className="text-base text-gray-900">
                    {validated_data.industry}
                  </dd>
                </div>
              )}

              {/* Employee Count */}
              {validated_data.employee_count && (
                <div>
                  <dt className="text-sm font-medium text-gray-500 mb-1">
                    Employee Count
                  </dt>
                  <dd className="text-base text-gray-900">
                    {validated_data.employee_count}
                  </dd>
                </div>
              )}

              {/* Headquarters */}
              {validated_data.headquarters && (
                <div>
                  <dt className="text-sm font-medium text-gray-500 mb-1">
                    Headquarters
                  </dt>
                  <dd className="text-base text-gray-900">
                    {validated_data.headquarters}
                  </dd>
                </div>
              )}

              {/* Founded Year */}
              {validated_data.founded_year && (
                <div>
                  <dt className="text-sm font-medium text-gray-500 mb-1">
                    Founded
                  </dt>
                  <dd className="text-base text-gray-900">
                    {validated_data.founded_year}
                  </dd>
                </div>
              )}

              {/* Revenue */}
              {validated_data.revenue && (
                <div>
                  <dt className="text-sm font-medium text-gray-500 mb-1">
                    Revenue
                  </dt>
                  <dd className="text-base text-gray-900">
                    {validated_data.revenue}
                  </dd>
                </div>
              )}

              {/* CEO */}
              {validated_data.ceo && (
                <div>
                  <dt className="text-sm font-medium text-gray-500 mb-1">
                    CEO
                  </dt>
                  <dd className="text-base text-gray-900">
                    {validated_data.ceo}
                  </dd>
                </div>
              )}

              {/* Target Market */}
              {validated_data.target_market && (
                <div>
                  <dt className="text-sm font-medium text-gray-500 mb-1">
                    Target Market
                  </dt>
                  <dd className="text-base text-gray-900">
                    {validated_data.target_market}
                  </dd>
                </div>
              )}

              {/* Geographic Reach */}
              {validated_data.geographic_reach && (
                <div>
                  <dt className="text-sm font-medium text-gray-500 mb-1">
                    Geographic Reach
                  </dt>
                  <dd className="text-base text-gray-900">
                    {validated_data.geographic_reach}
                  </dd>
                </div>
              )}
            </dl>

            {/* Technology Stack */}
            {validated_data.technology && validated_data.technology.length > 0 && (
              <div className="mt-6 pt-6 border-t border-gray-200">
                <dt className="text-sm font-medium text-gray-500 mb-2">
                  Technology Stack
                </dt>
                <dd className="flex flex-wrap gap-2">
                  {validated_data.technology.map((tech, index) => (
                    <span
                      key={index}
                      className="px-3 py-1 bg-gray-100 text-gray-800 text-sm rounded-full"
                    >
                      {tech}
                    </span>
                  ))}
                </dd>
              </div>
            )}

            {/* Contact Information */}
            {validated_data.contacts && (
              <div className="mt-6 pt-6 border-t border-gray-200">
                <dt className="text-sm font-medium text-gray-500 mb-3">
                  Contact Information
                </dt>
                <dd className="space-y-2">
                  {validated_data.contacts.website && (
                    <div className="flex items-center text-sm">
                      <span className="text-gray-600 w-20">Website:</span>
                      <a
                        href={`https://${validated_data.contacts.website}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary-600 hover:underline"
                      >
                        {validated_data.contacts.website}
                      </a>
                    </div>
                  )}
                  {validated_data.contacts.linkedin && (
                    <div className="flex items-center text-sm">
                      <span className="text-gray-600 w-20">LinkedIn:</span>
                      <a
                        href={validated_data.contacts.linkedin}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary-600 hover:underline"
                      >
                        View Profile
                      </a>
                    </div>
                  )}
                  {validated_data.contacts.email && (
                    <div className="flex items-center text-sm">
                      <span className="text-gray-600 w-20">Email:</span>
                      <a
                        href={`mailto:${validated_data.contacts.email}`}
                        className="text-primary-600 hover:underline"
                      >
                        {validated_data.contacts.email}
                      </a>
                    </div>
                  )}
                </dd>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Success Message */}
      <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
        <p className="text-sm text-green-800">
          Profile generated successfully! The data has been validated using
          multiple sources and LLM-based conflict resolution.
        </p>
      </div>
    </div>
  );
}
