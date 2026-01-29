'use client';

import type { SalesProgram, IntentLevel } from '@/types';

interface SalesProgramCardProps {
  program: SalesProgram;
}

const intentLevelConfig: Record<IntentLevel, {
  color: string;
  bgColor: string;
  ringColor: string;
  barColor: string;
  description: string;
}> = {
  'Low': {
    color: 'text-slate-700',
    bgColor: 'bg-slate-100',
    ringColor: 'ring-slate-600/20',
    barColor: 'bg-slate-400',
    description: 'Early awareness stage - focus on education and relationship building',
  },
  'Medium': {
    color: 'text-amber-700',
    bgColor: 'bg-amber-100',
    ringColor: 'ring-amber-600/20',
    barColor: 'bg-amber-500',
    description: 'Active research stage - provide solution comparisons and case studies',
  },
  'High': {
    color: 'text-emerald-700',
    bgColor: 'bg-emerald-100',
    ringColor: 'ring-emerald-600/20',
    barColor: 'bg-emerald-500',
    description: 'Evaluation stage - offer demos, trials, and detailed ROI analysis',
  },
  'Very High': {
    color: 'text-primary-700',
    bgColor: 'bg-primary-100',
    ringColor: 'ring-primary-600/20',
    barColor: 'bg-primary-500',
    description: 'Decision stage - prioritize for immediate outreach with tailored proposals',
  },
};

function getIntentBarWidth(score: number): string {
  if (score <= 25) return 'w-1/4';
  if (score <= 50) return 'w-2/4';
  if (score <= 75) return 'w-3/4';
  return 'w-full';
}

export default function SalesProgramCard({ program }: SalesProgramCardProps) {
  const config = intentLevelConfig[program.intentLevel] || intentLevelConfig['Low'];
  const normalizedScore = Math.min(100, Math.max(0, program.intentScore));

  return (
    <div className="card p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Sales Program</h2>
            <p className="text-sm text-slate-500">Recommended engagement strategy</p>
          </div>
        </div>
        <span className={`inline-flex items-center px-3 py-1.5 rounded-full text-sm font-semibold ring-1 ring-inset ${config.bgColor} ${config.color} ${config.ringColor}`}>
          {program.intentLevel} Intent
        </span>
      </div>

      {/* Intent Score Meter */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-slate-700">Intent Score</span>
          <span className={`text-sm font-bold ${config.color}`}>{normalizedScore}/100</span>
        </div>
        <div className="w-full bg-slate-100 rounded-full h-3 overflow-hidden">
          <div
            className={`${config.barColor} h-3 rounded-full transition-all duration-700 ease-out`}
            style={{ width: `${normalizedScore}%` }}
          />
        </div>
        <p className="text-xs text-slate-500 mt-2">{config.description}</p>
      </div>

      {/* Strategy Text */}
      <div className="bg-slate-50 rounded-xl p-4">
        <h3 className="text-sm font-medium text-slate-700 mb-2 flex items-center">
          <svg className="w-4 h-4 mr-2 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          Recommended Strategy
        </h3>
        <p className="text-sm text-slate-600 leading-relaxed">
          {program.strategyText || 'No specific strategy recommendations available.'}
        </p>
      </div>

      {/* Quick Action Buttons */}
      <div className="mt-4 flex flex-wrap gap-2">
        <button className="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-medium bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 transition-colors">
          <svg className="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          Schedule Follow-up
        </button>
        <button className="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-medium bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 transition-colors">
          <svg className="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          Export to CRM
        </button>
      </div>
    </div>
  );
}
