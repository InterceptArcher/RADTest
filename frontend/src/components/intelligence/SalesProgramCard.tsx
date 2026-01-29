'use client';

import { useState } from 'react';
import type { SalesProgram, IntentLevel, StakeholderRoleType } from '@/types';

interface SalesProgramCardProps {
  program: SalesProgram;
  onGenerateOutreach?: (roleType: StakeholderRoleType) => void;
}

const intentLevelConfig: Record<IntentLevel, {
  color: string;
  bgColor: string;
  ringColor: string;
  barColor: string;
  stage: string;
  description: string;
  strategyDefault: string;
}> = {
  'Low': {
    color: 'text-slate-700',
    bgColor: 'bg-slate-100',
    ringColor: 'ring-slate-600/20',
    barColor: 'bg-slate-400',
    stage: 'Early Curiosity',
    description: 'Initial awareness stage – building familiarity with the brand',
    strategyDefault: 'Introduce emerging trends and thought leadership to build awareness and credibility. Focus on educational content that addresses industry challenges without being overly promotional.',
  },
  'Medium': {
    color: 'text-amber-700',
    bgColor: 'bg-amber-100',
    ringColor: 'ring-amber-600/20',
    barColor: 'bg-amber-500',
    stage: 'Problem Acknowledgement',
    description: 'Recognizing challenges – actively researching solutions',
    strategyDefault: 'Highlight business challenges and frame solutions as ways to address them. Provide comparative analysis and industry benchmarks to help the prospect evaluate options.',
  },
  'High': {
    color: 'text-emerald-700',
    bgColor: 'bg-emerald-100',
    ringColor: 'ring-emerald-600/20',
    barColor: 'bg-emerald-500',
    stage: 'Active Evaluation',
    description: 'Comparing vendors – requesting demos and pricing',
    strategyDefault: 'Reinforce proof points with case studies and demonstrate integration value. Offer personalized demos, POCs, and detailed technical documentation to support evaluation.',
  },
  'Very High': {
    color: 'text-primary-700',
    bgColor: 'bg-primary-100',
    ringColor: 'ring-primary-600/20',
    barColor: 'bg-primary-500',
    stage: 'Decision',
    description: 'Ready to buy – finalizing vendor selection',
    strategyDefault: 'Emphasize ROI, deployment support, and the ease of scaling. Provide executive-level business cases, implementation timelines, and success metrics.',
  },
};

const targetRoles: StakeholderRoleType[] = ['CIO', 'CTO', 'CISO', 'COO', 'CFO', 'CPO'];

export default function SalesProgramCard({ program, onGenerateOutreach }: SalesProgramCardProps) {
  const [expanded, setExpanded] = useState(false);
  const config = intentLevelConfig[program.intentLevel] || intentLevelConfig['Low'];
  const normalizedScore = Math.min(100, Math.max(0, program.intentScore));

  return (
    <div className="card overflow-hidden">
      {/* Clickable Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-6 text-left hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Recommended Sales Program</h2>
              <p className="text-sm text-slate-500">Strategy based on intent signals</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <span className={`inline-flex items-center px-3 py-1.5 rounded-full text-xs font-semibold ring-1 ring-inset ${config.bgColor} ${config.color} ${config.ringColor}`}>
              {program.intentLevel} Intent
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
            {/* Intent Score Bar */}
            <div className="mb-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-slate-500">Intent Score</span>
                <span className={`text-xs font-bold ${config.color}`}>{normalizedScore}/100</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2">
                <div
                  className={`${config.barColor} h-2 rounded-full transition-all duration-500`}
                  style={{ width: `${normalizedScore}%` }}
                />
              </div>
            </div>
            <p className="text-xs text-slate-600">
              <span className="font-medium">{config.stage}</span> – {config.description}
            </p>
          </div>
        )}
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="px-6 pb-6 border-t border-slate-100">
          {/* Strategy Logic Section */}
          <div className="mt-6">
            <h3 className="text-sm font-semibold text-slate-900 mb-4 flex items-center">
              <svg className="w-4 h-4 mr-2 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              Strategy Logic
            </h3>

            {/* Intent Level Indicator */}
            <div className="bg-white border border-slate-200 rounded-xl p-4 mb-4">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <p className="text-xs text-slate-500 mb-1">Current Intent Level</p>
                  <p className={`text-lg font-bold ${config.color}`}>{program.intentLevel}</p>
                </div>
                <div className={`w-16 h-16 rounded-full ${config.bgColor} flex items-center justify-center`}>
                  <span className={`text-2xl font-bold ${config.color}`}>{normalizedScore}</span>
                </div>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-3 mb-2">
                <div
                  className={`${config.barColor} h-3 rounded-full transition-all duration-700 ease-out`}
                  style={{ width: `${normalizedScore}%` }}
                />
              </div>
              <div className="flex justify-between text-[10px] text-slate-400">
                <span>Early Curiosity</span>
                <span>Problem Ack.</span>
                <span>Evaluation</span>
                <span>Decision</span>
              </div>
            </div>

            {/* Stage Description */}
            <div className={`${config.bgColor} rounded-xl p-4 mb-4`}>
              <div className="flex items-start space-x-3">
                <div className={`w-8 h-8 rounded-lg bg-white/80 flex items-center justify-center flex-shrink-0`}>
                  <svg className={`w-4 h-4 ${config.color}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <p className={`text-sm font-semibold ${config.color} mb-1`}>{config.stage}</p>
                  <p className="text-sm text-slate-700">{config.description}</p>
                </div>
              </div>
            </div>

            {/* Strategy Text */}
            <div className="bg-white border border-slate-200 rounded-xl p-4">
              <h4 className="text-xs font-semibold text-slate-700 mb-2 uppercase tracking-wide">
                Recommended Strategy
              </h4>
              <p className="text-sm text-slate-600 leading-relaxed">
                {program.strategyText || config.strategyDefault}
              </p>
            </div>
          </div>

          {/* All Intent Level Strategies Reference */}
          <div className="mt-6">
            <h3 className="text-sm font-semibold text-slate-900 mb-3 flex items-center">
              <svg className="w-4 h-4 mr-2 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
              </svg>
              Strategy by Intent Level
            </h3>
            <div className="space-y-2">
              {(['Low', 'Medium', 'High', 'Very High'] as IntentLevel[]).map((level) => {
                const levelConfig = intentLevelConfig[level];
                const isActive = program.intentLevel === level;
                return (
                  <div
                    key={level}
                    className={`rounded-lg p-3 border ${isActive ? `${levelConfig.bgColor} border-${levelConfig.color.replace('text-', '')}` : 'bg-slate-50 border-slate-200'}`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className={`text-xs font-semibold ${isActive ? levelConfig.color : 'text-slate-600'}`}>
                        {level} Intent – {levelConfig.stage}
                      </span>
                      {isActive && (
                        <span className="text-[10px] font-medium text-emerald-600 bg-emerald-100 px-2 py-0.5 rounded-full">
                          Current
                        </span>
                      )}
                    </div>
                    <p className={`text-xs ${isActive ? 'text-slate-700' : 'text-slate-500'}`}>
                      {levelConfig.strategyDefault.slice(0, 100)}...
                    </p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Supporting Assets Section */}
          <div className="mt-6">
            <h3 className="text-sm font-semibold text-slate-900 mb-2 flex items-center">
              <svg className="w-4 h-4 mr-2 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Supporting Assets (Generative Content)
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              Generate personalized outreach content for each stakeholder role
            </p>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {targetRoles.map((role) => (
                <button
                  key={role}
                  onClick={() => onGenerateOutreach?.(role)}
                  disabled={!onGenerateOutreach}
                  className="bg-white border border-slate-200 rounded-xl p-4 text-left hover:border-primary-300 hover:bg-primary-50 transition-all group disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-semibold text-slate-900">{role}</span>
                    <svg className="w-4 h-4 text-slate-400 group-hover:text-primary-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                    </svg>
                  </div>
                  <div className="space-y-1 text-[10px] text-slate-500">
                    <div className="flex items-center">
                      <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                      </svg>
                      Email Copy
                    </div>
                    <div className="flex items-center">
                      <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z" />
                      </svg>
                      LinkedIn Copy
                    </div>
                    <div className="flex items-center">
                      <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                      </svg>
                      Call Script
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Quick Action Buttons */}
          <div className="mt-6 flex flex-wrap gap-2">
            <button className="inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 transition-colors">
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              Schedule Follow-up
            </button>
            <button className="inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 transition-colors">
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              Export to CRM
            </button>
            <button className="inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 transition-colors">
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download Report
            </button>
          </div>

          {/* Data Source Note */}
          <div className="mt-6 flex items-start space-x-2 text-xs text-slate-500 bg-slate-50 rounded-lg p-3">
            <svg className="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p>Sales strategy recommendations are AI-generated based on aggregated buying signals, intent data, and account firmographics. Outreach content is personalized to each stakeholder role.</p>
          </div>
        </div>
      )}
    </div>
  );
}
