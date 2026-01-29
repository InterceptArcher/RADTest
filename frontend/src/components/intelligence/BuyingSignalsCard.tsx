'use client';

import { useState } from 'react';
import type { BuyingSignals, Scoop } from '@/types';

interface BuyingSignalsCardProps {
  signals: BuyingSignals;
}

const signalStrengthConfig = {
  low: { label: 'Low', color: 'bg-slate-400', width: 'w-1/4', textColor: 'text-slate-600', value: 25 },
  medium: { label: 'Medium', color: 'bg-amber-400', width: 'w-2/4', textColor: 'text-amber-600', value: 50 },
  high: { label: 'High', color: 'bg-emerald-500', width: 'w-3/4', textColor: 'text-emerald-600', value: 75 },
  very_high: { label: 'Very High', color: 'bg-primary-500', width: 'w-full', textColor: 'text-primary-600', value: 100 },
};

const scoopTypeConfig: Record<Scoop['type'], {
  icon: React.ReactNode;
  bg: string;
  text: string;
  title: string;
  description: string;
}> = {
  executive_hire: {
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
      </svg>
    ),
    bg: 'bg-blue-100',
    text: 'text-blue-700',
    title: 'Executive Hires',
    description: 'New leaders often bring new vendor preferences – key opportunity for engagement.',
  },
  funding: {
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    bg: 'bg-emerald-100',
    text: 'text-emerald-700',
    title: 'Funding Rounds',
    description: 'New capital often means new spending – budget availability signal.',
  },
  expansion: {
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
      </svg>
    ),
    bg: 'bg-purple-100',
    text: 'text-purple-700',
    title: 'Expansions',
    description: 'New markets indicate expanded infrastructure needs – growth opportunity.',
  },
  merger_acquisition: {
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
      </svg>
    ),
    bg: 'bg-orange-100',
    text: 'text-orange-700',
    title: 'M&A Activity',
    description: 'Org changes indicate integration and vendor consolidation needs.',
  },
  product_launch: {
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.631 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 01-2.448-2.448 14.9 14.9 0 01.06-.312m-2.24 2.39a4.493 4.493 0 00-1.757 4.306 4.493 4.493 0 004.306-1.758M16.5 9a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z" />
      </svg>
    ),
    bg: 'bg-pink-100',
    text: 'text-pink-700',
    title: 'Product Launch',
    description: 'New products may require supporting technology and infrastructure.',
  },
  other: {
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    bg: 'bg-slate-100',
    text: 'text-slate-700',
    title: 'Other Signals',
    description: 'Additional market intelligence and trigger events.',
  },
};

// Group scoops by type
function groupScoopsByType(scoops: Scoop[]) {
  const groups: Record<string, Scoop[]> = {};
  scoops.forEach(scoop => {
    if (!groups[scoop.type]) {
      groups[scoop.type] = [];
    }
    groups[scoop.type].push(scoop);
  });
  return groups;
}

export default function BuyingSignalsCard({ signals }: BuyingSignalsCardProps) {
  const [expanded, setExpanded] = useState(false);
  const strength = signalStrengthConfig[signals.signalStrength] || signalStrengthConfig.low;
  const groupedScoops = signals.scoops ? groupScoopsByType(signals.scoops) : {};
  const topIntentTopics = signals.intentTopics?.slice(0, 3) || [];

  return (
    <div className="card overflow-hidden">
      {/* Clickable Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-6 text-left hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Buying Signals</h2>
              <p className="text-sm text-slate-500">Intent indicators and triggers</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${strength.textColor} bg-opacity-20`}>
              {strength.label} Intent
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
          <div className="mt-4">
            {/* Signal Strength Bar */}
            <div className="mb-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-slate-500">Signal Strength</span>
                <span className={`text-xs font-semibold ${strength.textColor}`}>{strength.label}</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2">
                <div className={`${strength.color} h-2 rounded-full transition-all duration-500 ${strength.width}`} />
              </div>
            </div>
            {/* Top Intent Topics Preview */}
            {topIntentTopics.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {topIntentTopics.map((topic, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-600/20"
                  >
                    {topic}
                  </span>
                ))}
                {signals.intentTopics && signals.intentTopics.length > 3 && (
                  <span className="text-xs text-slate-500">+{signals.intentTopics.length - 3} more</span>
                )}
              </div>
            )}
          </div>
        )}
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="px-6 pb-6 border-t border-slate-100">
          {/* Active Buying Signals Section */}
          <div className="mt-6">
            <h3 className="text-sm font-semibold text-slate-900 mb-4 flex items-center">
              <svg className="w-4 h-4 mr-2 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Active Buying Signals
            </h3>

            {/* Signal Strength Meter */}
            <div className="bg-white border border-slate-200 rounded-xl p-4 mb-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-slate-700">Overall Signal Strength</span>
                <span className={`text-sm font-bold ${strength.textColor}`}>{strength.value}%</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-3 mb-2">
                <div
                  className={`${strength.color} h-3 rounded-full transition-all duration-500`}
                  style={{ width: `${strength.value}%` }}
                />
              </div>
              <p className="text-xs text-slate-500">
                Based on intent topics, scoops, and engagement signals
              </p>
            </div>

            {/* Top Intent Topics */}
            <div className="bg-white border border-slate-200 rounded-xl p-4 mb-4">
              <h4 className="text-xs font-semibold text-slate-700 mb-3 uppercase tracking-wide">
                Top Intent Topics
              </h4>
              {signals.intentTopics && signals.intentTopics.length > 0 ? (
                <div className="space-y-2">
                  {signals.intentTopics.map((topic, index) => (
                    <div key={index} className="flex items-center">
                      <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold mr-3 ${
                        index === 0 ? 'bg-amber-500 text-white' :
                        index === 1 ? 'bg-amber-400 text-white' :
                        index === 2 ? 'bg-amber-300 text-amber-800' :
                        'bg-slate-200 text-slate-600'
                      }`}>
                        {index + 1}
                      </span>
                      <span className="text-sm text-slate-900">{topic}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-500">No intent topics detected</p>
              )}
            </div>

            {/* Trend Chart Placeholder */}
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 mb-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wide">
                  Intent Trend (30 Days)
                </h4>
                <span className="text-xs text-slate-500">Coming soon</span>
              </div>
              <div className="h-24 flex items-center justify-center bg-slate-100 rounded-lg">
                <div className="text-center">
                  <svg className="w-8 h-8 mx-auto text-slate-400 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
                  </svg>
                  <p className="text-xs text-slate-500">Signal trend visualization</p>
                </div>
              </div>
              <p className="text-xs text-slate-500 mt-2">
                Shows intent signal strength over time based on content engagement and research activity.
              </p>
            </div>
          </div>

          {/* Scoops Section */}
          <div className="mt-6">
            <h3 className="text-sm font-semibold text-slate-900 mb-2 flex items-center">
              <svg className="w-4 h-4 mr-2 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
              </svg>
              Scoops & Triggers
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              News, events, and triggers that indicate potential buying activity
            </p>

            {Object.keys(groupedScoops).length > 0 ? (
              <div className="space-y-4">
                {Object.entries(groupedScoops).map(([type, scoops]) => {
                  const config = scoopTypeConfig[type as Scoop['type']] || scoopTypeConfig.other;
                  return (
                    <div key={type} className="bg-white border border-slate-200 rounded-xl overflow-hidden">
                      <div className={`${config.bg} px-4 py-3 border-b border-slate-200`}>
                        <div className="flex items-center space-x-2">
                          <span className={config.text}>{config.icon}</span>
                          <h4 className={`text-sm font-semibold ${config.text}`}>{config.title}</h4>
                        </div>
                        <p className="text-xs text-slate-600 mt-1">{config.description}</p>
                      </div>
                      <div className="p-4 space-y-3">
                        {scoops.map((scoop, idx) => (
                          <div key={idx} className="flex items-start space-x-3">
                            <div className="w-2 h-2 rounded-full bg-slate-300 mt-2 flex-shrink-0" />
                            <div>
                              <p className="text-sm font-medium text-slate-900">{scoop.title}</p>
                              {scoop.date && (
                                <p className="text-xs text-slate-500 mt-0.5">{scoop.date}</p>
                              )}
                              <p className="text-xs text-slate-600 mt-1">{scoop.details}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="bg-slate-50 rounded-xl p-6 text-center">
                <svg className="w-8 h-8 mx-auto text-slate-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
                </svg>
                <p className="text-sm text-slate-500">No scoops available</p>
                <p className="text-xs text-slate-400 mt-1">News and trigger events will appear here when detected</p>
              </div>
            )}
          </div>

          {/* Opportunity Themes Section */}
          <div className="mt-6">
            <h3 className="text-sm font-semibold text-slate-900 mb-2 flex items-center">
              <svg className="w-4 h-4 mr-2 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              Opportunity Themes
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              Organizational challenges mapped to solution categories
            </p>

            {signals.opportunityThemes && signals.opportunityThemes.length > 0 ? (
              <div className="space-y-3">
                {signals.opportunityThemes.map((theme, index) => (
                  <div key={index} className="bg-white border border-slate-200 rounded-xl p-4">
                    <div className="flex items-center mb-2">
                      <span className="w-6 h-6 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center text-xs font-bold mr-2">
                        {index + 1}
                      </span>
                      <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Priority {index + 1}</span>
                    </div>
                    <div className="grid md:grid-cols-2 gap-4">
                      <div className="bg-red-50 rounded-lg p-3">
                        <p className="text-xs font-medium text-red-700 mb-1">Challenge</p>
                        <p className="text-sm text-red-900">{theme.challenge}</p>
                      </div>
                      <div className="bg-emerald-50 rounded-lg p-3">
                        <p className="text-xs font-medium text-emerald-700 mb-1">Solution Category</p>
                        <p className="text-sm text-emerald-900">{theme.solutionCategory}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-slate-50 rounded-xl p-6 text-center">
                <svg className="w-8 h-8 mx-auto text-slate-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                <p className="text-sm text-slate-500">No opportunity themes identified</p>
                <p className="text-xs text-slate-400 mt-1">Challenge-to-solution mappings will appear here</p>
              </div>
            )}
          </div>

          {/* Data Source Note */}
          <div className="mt-6 flex items-start space-x-2 text-xs text-slate-500 bg-slate-50 rounded-lg p-3">
            <svg className="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p>Intent data derived from content engagement, research activity, and market signals. Scoops sourced from news APIs and company announcements.</p>
          </div>
        </div>
      )}
    </div>
  );
}
