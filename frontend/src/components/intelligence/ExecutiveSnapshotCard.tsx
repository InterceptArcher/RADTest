'use client';

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

const techCategoryColors: Record<string, string> = {
  crm: 'bg-blue-100 text-blue-700',
  marketing: 'bg-pink-100 text-pink-700',
  sales: 'bg-green-100 text-green-700',
  infrastructure: 'bg-orange-100 text-orange-700',
  analytics: 'bg-purple-100 text-purple-700',
  security: 'bg-red-100 text-red-700',
  productivity: 'bg-teal-100 text-teal-700',
  hr: 'bg-indigo-100 text-indigo-700',
  finance: 'bg-emerald-100 text-emerald-700',
  default: 'bg-slate-100 text-slate-700',
};

function getTechCategoryColor(category: string): string {
  const normalizedCategory = category.toLowerCase().replace(/[_\s-]/g, '');
  for (const [key, value] of Object.entries(techCategoryColors)) {
    if (normalizedCategory.includes(key)) {
      return value;
    }
  }
  return techCategoryColors.default;
}

export default function ExecutiveSnapshotCard({
  snapshot,
  companyName,
  industry,
}: ExecutiveSnapshotCardProps) {
  const classification = classificationConfig[snapshot.companyClassification] || classificationConfig.Unknown;

  return (
    <div className="card p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
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
        <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ring-1 ring-inset ${classification.bg} ${classification.text} ${classification.ring}`}>
          {snapshot.companyClassification}
        </span>
      </div>

      {/* Company Overview */}
      <div className="mb-6">
        <h3 className="text-sm font-medium text-slate-700 mb-2">Company Overview</h3>
        <p className="text-sm text-slate-600 leading-relaxed">
          {snapshot.companyOverview || 'Company overview not available.'}
        </p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        {industry && (
          <div className="bg-slate-50 rounded-xl p-4">
            <p className="text-xs text-slate-500 mb-1">Industry</p>
            <p className="text-sm font-semibold text-slate-900">{industry}</p>
          </div>
        )}
        {snapshot.estimatedITSpend && (
          <div className="bg-emerald-50 rounded-xl p-4">
            <p className="text-xs text-emerald-600 mb-1">Est. IT Spend</p>
            <p className="text-sm font-semibold text-emerald-700">{snapshot.estimatedITSpend}</p>
          </div>
        )}
      </div>

      {/* Technology Stack */}
      {snapshot.technologyStack && snapshot.technologyStack.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-slate-700 mb-3">Technology Stack</h3>
          <div className="flex flex-wrap gap-2">
            {snapshot.technologyStack.map((tech, index) => (
              <div
                key={`${tech.name}-${index}`}
                className={`inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-medium ${getTechCategoryColor(tech.category)}`}
                title={tech.lastSeen ? `Last seen: ${tech.lastSeen}` : undefined}
              >
                <span>{tech.name}</span>
                {tech.lastSeen && (
                  <span className="ml-1.5 opacity-60 text-[10px]">
                    ({tech.lastSeen})
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State for Tech Stack */}
      {(!snapshot.technologyStack || snapshot.technologyStack.length === 0) && (
        <div className="text-center py-4 text-sm text-slate-400">
          Technology stack data unavailable
        </div>
      )}
    </div>
  );
}
