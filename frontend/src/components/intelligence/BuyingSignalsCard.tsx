'use client';

import type { BuyingSignals, Scoop } from '@/types';

interface BuyingSignalsCardProps {
  signals: BuyingSignals;
}

const signalStrengthConfig = {
  low: { label: 'Low', color: 'bg-slate-400', width: 'w-1/4', textColor: 'text-slate-600' },
  medium: { label: 'Medium', color: 'bg-amber-400', width: 'w-2/4', textColor: 'text-amber-600' },
  high: { label: 'High', color: 'bg-emerald-500', width: 'w-3/4', textColor: 'text-emerald-600' },
  very_high: { label: 'Very High', color: 'bg-primary-500', width: 'w-full', textColor: 'text-primary-600' },
};

const scoopTypeConfig: Record<Scoop['type'], { icon: React.ReactNode; bg: string; text: string }> = {
  executive_hire: {
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
      </svg>
    ),
    bg: 'bg-blue-100',
    text: 'text-blue-700',
  },
  funding: {
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    bg: 'bg-emerald-100',
    text: 'text-emerald-700',
  },
  expansion: {
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
      </svg>
    ),
    bg: 'bg-purple-100',
    text: 'text-purple-700',
  },
  merger_acquisition: {
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
      </svg>
    ),
    bg: 'bg-orange-100',
    text: 'text-orange-700',
  },
  product_launch: {
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.631 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 01-2.448-2.448 14.9 14.9 0 01.06-.312m-2.24 2.39a4.493 4.493 0 00-1.757 4.306 4.493 4.493 0 004.306-1.758M16.5 9a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z" />
      </svg>
    ),
    bg: 'bg-pink-100',
    text: 'text-pink-700',
  },
  other: {
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    bg: 'bg-slate-100',
    text: 'text-slate-700',
  },
};

export default function BuyingSignalsCard({ signals }: BuyingSignalsCardProps) {
  const strength = signalStrengthConfig[signals.signalStrength] || signalStrengthConfig.low;

  return (
    <div className="card p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
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
      </div>

      {/* Signal Strength Meter */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-slate-700">Signal Strength</span>
          <span className={`text-sm font-semibold ${strength.textColor}`}>{strength.label}</span>
        </div>
        <div className="w-full bg-slate-100 rounded-full h-2.5">
          <div className={`${strength.color} h-2.5 rounded-full transition-all duration-500 ${strength.width}`} />
        </div>
      </div>

      {/* Intent Topics */}
      {signals.intentTopics && signals.intentTopics.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-medium text-slate-700 mb-3">Intent Topics</h3>
          <div className="flex flex-wrap gap-2">
            {signals.intentTopics.map((topic, index) => (
              <span
                key={index}
                className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-600/20"
              >
                {topic}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Scoops Timeline */}
      {signals.scoops && signals.scoops.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-medium text-slate-700 mb-3">Scoops & Triggers</h3>
          <div className="space-y-3">
            {signals.scoops.map((scoop, index) => {
              const config = scoopTypeConfig[scoop.type] || scoopTypeConfig.other;
              return (
                <div key={index} className="flex items-start space-x-3">
                  <div className={`w-8 h-8 rounded-lg ${config.bg} flex items-center justify-center flex-shrink-0`}>
                    <span className={config.text}>{config.icon}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <p className="text-sm font-medium text-slate-900 truncate">{scoop.title}</p>
                      {scoop.date && (
                        <span className="text-xs text-slate-400 flex-shrink-0">{scoop.date}</span>
                      )}
                    </div>
                    <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{scoop.details}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Opportunity Themes */}
      {signals.opportunityThemes && signals.opportunityThemes.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-slate-700 mb-3">Opportunity Themes</h3>
          <div className="space-y-2">
            {signals.opportunityThemes.map((theme, index) => (
              <div key={index} className="flex items-center bg-slate-50 rounded-lg p-3">
                <div className="flex-1">
                  <p className="text-xs text-slate-500">Challenge</p>
                  <p className="text-sm font-medium text-slate-900">{theme.challenge}</p>
                </div>
                <svg className="w-5 h-5 text-slate-400 mx-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
                <div className="flex-1">
                  <p className="text-xs text-slate-500">Solution</p>
                  <p className="text-sm font-medium text-primary-600">{theme.solutionCategory}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {(!signals.intentTopics || signals.intentTopics.length === 0) &&
       (!signals.scoops || signals.scoops.length === 0) &&
       (!signals.opportunityThemes || signals.opportunityThemes.length === 0) && (
        <div className="text-center py-4 text-sm text-slate-400">
          No buying signals detected
        </div>
      )}
    </div>
  );
}
