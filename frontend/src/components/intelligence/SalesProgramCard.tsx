'use client';

import { useState } from 'react';
import type { SalesProgram, IntentLevel } from '@/types';

interface SalesProgramCardProps {
  program: SalesProgram;
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

// Conversation starters based on intent level
const conversationStartersByIntent: Record<IntentLevel, string[]> = {
  'Low': [
    "I noticed your company has been exploring solutions in this space. What challenges are you currently facing?",
    "Many organizations in your industry are starting to evaluate options for [solution area]. Is this something on your radar?",
    "I came across some interesting trends affecting companies like yours. Would you be open to a brief conversation about how others are approaching this?"
  ],
  'Medium': [
    "Based on your recent activity, it seems like [topic] is becoming a priority. What's driving that interest?",
    "I see you've been researching solutions in this area. How does your current approach compare to what you're evaluating?",
    "Companies at a similar stage often benefit from understanding the ROI others have achieved. Would a case study be helpful?"
  ],
  'High': [
    "It looks like you're actively evaluating vendors. What criteria matter most to your team?",
    "I'd love to understand your timeline and what a successful implementation would look like for you.",
    "Many of our customers in your situation found a technical deep-dive valuable at this stage. Would that be useful?"
  ],
  'Very High': [
    "I understand you're close to a decision. What would help you feel confident in your choice?",
    "At this stage, stakeholder alignment is often key. Who else needs to be involved in the final decision?",
    "Let's discuss implementation specifics and how we can ensure a smooth transition for your team."
  ]
};

// Next steps based on intent level
const nextStepsByIntent: Record<IntentLevel, { action: string; description: string }[]> = {
  'Low': [
    { action: "Share educational content", description: "Send industry report or thought leadership piece" },
    { action: "Connect on LinkedIn", description: "Build relationship with personalized connection request" },
    { action: "Add to nurture sequence", description: "Enroll in automated awareness campaign" }
  ],
  'Medium': [
    { action: "Schedule discovery call", description: "15-minute conversation to understand needs" },
    { action: "Send relevant case study", description: "Share success story from similar company" },
    { action: "Invite to upcoming webinar", description: "Educational event relevant to their challenges" }
  ],
  'High': [
    { action: "Offer personalized demo", description: "Tailored demonstration of key features" },
    { action: "Propose POC/pilot program", description: "Limited trial to prove value" },
    { action: "Connect with technical team", description: "Arrange solution architect conversation" }
  ],
  'Very High': [
    { action: "Send custom proposal", description: "Detailed pricing and implementation plan" },
    { action: "Arrange executive meeting", description: "Align leadership on partnership vision" },
    { action: "Prepare implementation timeline", description: "Detailed onboarding and success roadmap" }
  ]
};

export default function SalesProgramCard({ program }: SalesProgramCardProps) {
  const [expanded, setExpanded] = useState(false);

  // Null safety for program data
  if (!program) {
    return null;
  }

  const config = intentLevelConfig[program.intentLevel] || intentLevelConfig['Low'];
  const normalizedScore = Math.min(100, Math.max(0, program.intentScore || 0));

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

          {/* Conversation Starters Section */}
          <div className="mt-6">
            <h3 className="text-sm font-semibold text-slate-900 mb-2 flex items-center">
              <svg className="w-4 h-4 mr-2 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              Conversation Starters
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              Opening lines tailored to {program.intentLevel} intent prospects
            </p>

            <div className="space-y-3">
              {conversationStartersByIntent[program.intentLevel].map((starter, index) => (
                <div key={index} className="bg-white border border-slate-200 rounded-xl p-4">
                  <div className="flex items-start space-x-3">
                    <span className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">
                      {index + 1}
                    </span>
                    <p className="text-sm text-slate-700 leading-relaxed italic">&ldquo;{starter}&rdquo;</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Next Steps Section */}
          <div className="mt-6">
            <h3 className="text-sm font-semibold text-slate-900 mb-2 flex items-center">
              <svg className="w-4 h-4 mr-2 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              Recommended Next Steps
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              Outreach actions for {program.intentLevel} intent accounts
            </p>

            <div className="space-y-3">
              {nextStepsByIntent[program.intentLevel].map((step, index) => (
                <div key={index} className="bg-white border border-slate-200 rounded-xl p-4">
                  <div className="flex items-start space-x-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                      index === 0 ? 'bg-emerald-100' : index === 1 ? 'bg-blue-100' : 'bg-purple-100'
                    }`}>
                      <span className={`text-xs font-bold ${
                        index === 0 ? 'text-emerald-700' : index === 1 ? 'text-blue-700' : 'text-purple-700'
                      }`}>
                        {index + 1}
                      </span>
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-semibold text-slate-900">{step.action}</p>
                      <p className="text-xs text-slate-600 mt-1">{step.description}</p>
                    </div>
                    <svg className="w-5 h-5 text-slate-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                </div>
              ))}
            </div>
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
