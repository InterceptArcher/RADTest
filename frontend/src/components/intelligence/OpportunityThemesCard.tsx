'use client';

import { useState } from 'react';
import type { OpportunityThemesDetailed } from '@/types';

interface OpportunityThemesCardProps {
  themes: OpportunityThemesDetailed;
}

export default function OpportunityThemesCard({ themes }: OpportunityThemesCardProps) {
  const [expanded, setExpanded] = useState(false);

  // Null safety
  if (!themes) {
    return null;
  }

  const painPoints = themes.pain_points || [];
  const salesOpportunities = themes.sales_opportunities || [];
  const solutionAreas = themes.recommended_solution_areas || [];

  // Don't render if no data
  if (painPoints.length === 0 && salesOpportunities.length === 0 && solutionAreas.length === 0) {
    return null;
  }

  return (
    <div className="card overflow-hidden">
      {/* Clickable Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-6 text-left hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-500 flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Opportunity Themes</h2>
              <p className="text-sm text-slate-500">Pain points, opportunities & solutions</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold text-purple-700 bg-purple-100">
              {painPoints.length + salesOpportunities.length + solutionAreas.length} insights
            </span>
            <svg
              className={`w-5 h-5 text-slate-400 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>

        {/* Preview when collapsed */}
        {!expanded && (
          <div className="mt-4 grid grid-cols-3 gap-4">
            <div className="text-center p-3 bg-red-50 rounded-lg">
              <p className="text-2xl font-bold text-red-600">{painPoints.length}</p>
              <p className="text-xs text-red-700">Pain Points</p>
            </div>
            <div className="text-center p-3 bg-emerald-50 rounded-lg">
              <p className="text-2xl font-bold text-emerald-600">{salesOpportunities.length}</p>
              <p className="text-xs text-emerald-700">Sales Opps</p>
            </div>
            <div className="text-center p-3 bg-blue-50 rounded-lg">
              <p className="text-2xl font-bold text-blue-600">{solutionAreas.length}</p>
              <p className="text-xs text-blue-700">Solutions</p>
            </div>
          </div>
        )}
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="px-6 pb-6 border-t border-slate-100">
          {/* Pain Points Section */}
          {painPoints.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-semibold text-slate-900 mb-4 flex items-center">
                <svg className="w-4 h-4 mr-2 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                Pain Points
              </h3>
              <p className="text-xs text-slate-500 mb-4">
                Key challenges and obstacles the organization is facing
              </p>
              <div className="space-y-3">
                {painPoints.map((point, index) => (
                  <div key={index} className="bg-red-50 border border-red-100 rounded-xl p-4">
                    <div className="flex items-start">
                      <span className="w-6 h-6 rounded-full bg-red-500 text-white flex items-center justify-center text-xs font-bold mr-3 flex-shrink-0">
                        {index + 1}
                      </span>
                      <p className="text-sm text-red-900 leading-relaxed">{point}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Sales Opportunities Section */}
          {salesOpportunities.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-semibold text-slate-900 mb-4 flex items-center">
                <svg className="w-4 h-4 mr-2 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Sales Opportunities
              </h3>
              <p className="text-xs text-slate-500 mb-4">
                Where HP can provide value and win business
              </p>
              <div className="space-y-3">
                {salesOpportunities.map((opportunity, index) => (
                  <div key={index} className="bg-emerald-50 border border-emerald-100 rounded-xl p-4">
                    <div className="flex items-start">
                      <span className="w-6 h-6 rounded-full bg-emerald-500 text-white flex items-center justify-center text-xs font-bold mr-3 flex-shrink-0">
                        {index + 1}
                      </span>
                      <p className="text-sm text-emerald-900 leading-relaxed">{opportunity}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommended Solution Areas Section */}
          {solutionAreas.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-semibold text-slate-900 mb-4 flex items-center">
                <svg className="w-4 h-4 mr-2 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
                </svg>
                Recommended Solution Areas
              </h3>
              <p className="text-xs text-slate-500 mb-4">
                Strategic recommendations based on identified pain points
              </p>
              <div className="space-y-3">
                {solutionAreas.map((area, index) => (
                  <div key={index} className="bg-blue-50 border border-blue-100 rounded-xl p-4">
                    <div className="flex items-start">
                      <span className="w-6 h-6 rounded-full bg-blue-500 text-white flex items-center justify-center text-xs font-bold mr-3 flex-shrink-0">
                        {index + 1}
                      </span>
                      <p className="text-sm text-blue-900 leading-relaxed">{area}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Data Source Note */}
          <div className="mt-6 flex items-start space-x-2 text-xs text-slate-500 bg-slate-50 rounded-lg p-3">
            <svg className="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p>Opportunity themes generated by AI analysis of company data, news, and market intelligence from multiple sources.</p>
          </div>
        </div>
      )}
    </div>
  );
}
