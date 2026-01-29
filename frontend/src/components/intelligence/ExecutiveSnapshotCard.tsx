'use client';

import { useState } from 'react';
import type { ExecutiveSnapshot } from '@/types';

interface ExecutiveSnapshotCardProps {
  snapshot: ExecutiveSnapshot;
  companyName: string;
  industry?: string;
}

const classificationConfig = {
  Public: { bg: 'bg-blue-50', text: 'text-blue-700', ring: 'ring-blue-600/20' },
  Private: { bg: 'bg-purple-50', text: 'text-purple-700', ring: 'ring-purple-600/20' },
  Government: { bg: 'bg-amber-50', text: 'text-amber-700', ring: 'ring-amber-600/20' },
  Unknown: { bg: 'bg-slate-50', text: 'text-slate-700', ring: 'ring-slate-600/20' },
};

const techCategoryConfig: Record<string, { label: string; color: string }> = {
  crm: { label: 'CRM', color: 'bg-blue-100 text-blue-700' },
  marketing_automation: { label: 'Marketing Automation', color: 'bg-pink-100 text-pink-700' },
  marketing: { label: 'Marketing', color: 'bg-pink-100 text-pink-700' },
  sales_tools: { label: 'Sales Tools', color: 'bg-green-100 text-green-700' },
  sales: { label: 'Sales', color: 'bg-green-100 text-green-700' },
  infrastructure: { label: 'Infrastructure', color: 'bg-orange-100 text-orange-700' },
  analytics: { label: 'Analytics', color: 'bg-purple-100 text-purple-700' },
  security: { label: 'Security', color: 'bg-red-100 text-red-700' },
  productivity: { label: 'Productivity', color: 'bg-teal-100 text-teal-700' },
  hr: { label: 'HR', color: 'bg-indigo-100 text-indigo-700' },
  finance: { label: 'Finance', color: 'bg-emerald-100 text-emerald-700' },
  cloud: { label: 'Cloud', color: 'bg-sky-100 text-sky-700' },
  data: { label: 'Data & Storage', color: 'bg-violet-100 text-violet-700' },
  default: { label: 'Other', color: 'bg-slate-100 text-slate-700' },
};

function getTechCategoryConfig(category: string): { label: string; color: string } {
  const normalizedCategory = category.toLowerCase().replace(/[\s-]/g, '_');
  return techCategoryConfig[normalizedCategory] || techCategoryConfig.default;
}

// Group technologies by category
function groupTechByCategory(technologies: Array<{name: string; category: string; lastSeen?: string}>) {
  const groups: Record<string, Array<{name: string; lastSeen?: string}>> = {};

  technologies.forEach(tech => {
    const category = tech.category || 'other';
    if (!groups[category]) {
      groups[category] = [];
    }
    groups[category].push({ name: tech.name, lastSeen: tech.lastSeen });
  });

  return groups;
}

export default function ExecutiveSnapshotCard({
  snapshot,
  companyName,
  industry,
}: ExecutiveSnapshotCardProps) {
  const [expanded, setExpanded] = useState(false);

  // Null safety for snapshot data
  if (!snapshot) {
    return null;
  }

  const classification = classificationConfig[snapshot.companyClassification] || classificationConfig.Unknown;
  const groupedTech = snapshot.technologyStack && Array.isArray(snapshot.technologyStack)
    ? groupTechByCategory(snapshot.technologyStack)
    : {};

  return (
    <div className="card overflow-hidden">
      {/* Clickable Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-6 text-left hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Executive Snapshot</h2>
              <p className="text-sm text-slate-500">Company overview and classification</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ring-1 ring-inset ${classification.bg} ${classification.text} ${classification.ring}`}>
              {snapshot.companyClassification}
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
          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-slate-50 rounded-lg p-3">
              <p className="text-xs text-slate-500">Company</p>
              <p className="text-sm font-medium text-slate-900 truncate">{companyName}</p>
            </div>
            {industry && (
              <div className="bg-slate-50 rounded-lg p-3">
                <p className="text-xs text-slate-500">Industry</p>
                <p className="text-sm font-medium text-slate-900 truncate">{industry}</p>
              </div>
            )}
            <div className="bg-slate-50 rounded-lg p-3">
              <p className="text-xs text-slate-500">Classification</p>
              <p className="text-sm font-medium text-slate-900">{snapshot.companyClassification}</p>
            </div>
            {snapshot.estimatedITSpend && (
              <div className="bg-emerald-50 rounded-lg p-3">
                <p className="text-xs text-emerald-600">Est. IT Spend</p>
                <p className="text-sm font-semibold text-emerald-700">{snapshot.estimatedITSpend}</p>
              </div>
            )}
          </div>
        )}
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="px-6 pb-6 border-t border-slate-100">
          {/* Company Overview */}
          <div className="mt-6">
            <h3 className="text-sm font-semibold text-slate-900 mb-2 flex items-center">
              <svg className="w-4 h-4 mr-2 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Company Overview
            </h3>
            <div className="bg-slate-50 rounded-xl p-4">
              <p className="text-sm text-slate-700 leading-relaxed">
                {snapshot.companyOverview || `${companyName} is a ${snapshot.companyClassification?.toLowerCase() || 'private'} company operating in the ${industry || 'technology'} sector. Additional company details are being gathered.`}
              </p>
            </div>
          </div>

          {/* Key Firmographics */}
          <div className="mt-6">
            <h3 className="text-sm font-semibold text-slate-900 mb-3 flex items-center">
              <svg className="w-4 h-4 mr-2 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              Key Firmographics
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white border border-slate-200 rounded-xl p-4">
                <p className="text-xs text-slate-500 mb-1">Company Name</p>
                <p className="text-sm font-semibold text-slate-900">{companyName}</p>
              </div>
              <div className="bg-white border border-slate-200 rounded-xl p-4">
                <p className="text-xs text-slate-500 mb-1">Sector</p>
                <p className="text-sm font-semibold text-slate-900">{snapshot.companyClassification || 'Private'}</p>
              </div>
              <div className="bg-white border border-slate-200 rounded-xl p-4">
                <p className="text-xs text-slate-500 mb-1">Industry</p>
                <p className="text-sm font-semibold text-slate-900">{industry || 'Not specified'}</p>
              </div>
              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
                <p className="text-xs text-emerald-600 mb-1">Est. Annual IT Spend</p>
                <p className="text-sm font-semibold text-emerald-700">{snapshot.estimatedITSpend || 'Not available'}</p>
              </div>
            </div>
          </div>

          {/* Technology Install Base */}
          <div className="mt-6">
            <h3 className="text-sm font-semibold text-slate-900 mb-3 flex items-center">
              <svg className="w-4 h-4 mr-2 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              Technology Install Base
            </h3>

            {Object.keys(groupedTech).length > 0 ? (
              <div className="space-y-4">
                {Object.entries(groupedTech).map(([category, techs]) => {
                  const categoryConfig = getTechCategoryConfig(category);
                  return (
                    <div key={category} className="bg-white border border-slate-200 rounded-xl p-4">
                      <h4 className="text-xs font-semibold text-slate-700 mb-3 uppercase tracking-wide">
                        {categoryConfig.label}
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {techs.map((tech, idx) => (
                          <div
                            key={`${tech.name}-${idx}`}
                            className={`inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-medium ${categoryConfig.color}`}
                          >
                            <span>{tech.name}</span>
                            {tech.lastSeen && (
                              <span className="ml-2 text-[10px] opacity-70 border-l border-current/20 pl-2">
                                Last seen: {tech.lastSeen}
                              </span>
                            )}
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
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                <p className="text-sm text-slate-500">Technology stack data not available</p>
                <p className="text-xs text-slate-400 mt-1">Install base information will appear here when available</p>
              </div>
            )}
          </div>

          {/* Data Source Note */}
          <div className="mt-6 flex items-start space-x-2 text-xs text-slate-500 bg-slate-50 rounded-lg p-3">
            <svg className="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p>Data sourced from PeopleDataLabs technographics and Apollo.io firmographics. IT spend estimates are AI-generated based on company size, industry, and technology footprint.</p>
          </div>
        </div>
      )}
    </div>
  );
}
