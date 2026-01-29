'use client';

import { useState } from 'react';
import type { StakeholderMap, Stakeholder, StakeholderRoleType } from '@/types';

interface StakeholderMapCardProps {
  stakeholderMap: StakeholderMap;
  onGenerateOutreach?: (roleType: StakeholderRoleType, stakeholderName?: string) => void;
}

const roleTypeConfig: Record<StakeholderRoleType, { color: string; bgColor: string }> = {
  CIO: { color: 'text-blue-700', bgColor: 'bg-blue-100' },
  CTO: { color: 'text-purple-700', bgColor: 'bg-purple-100' },
  CISO: { color: 'text-red-700', bgColor: 'bg-red-100' },
  COO: { color: 'text-emerald-700', bgColor: 'bg-emerald-100' },
  CFO: { color: 'text-amber-700', bgColor: 'bg-amber-100' },
  CPO: { color: 'text-pink-700', bgColor: 'bg-pink-100' },
  Unknown: { color: 'text-slate-700', bgColor: 'bg-slate-100' },
};

interface StakeholderCardProps {
  stakeholder: Stakeholder;
  onGenerateOutreach?: (roleType: StakeholderRoleType, stakeholderName?: string) => void;
}

function StakeholderCard({ stakeholder, onGenerateOutreach }: StakeholderCardProps) {
  const [expanded, setExpanded] = useState(false);
  const roleConfig = roleTypeConfig[stakeholder.roleType] || roleTypeConfig.Unknown;

  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden hover:border-primary-200 hover:shadow-md transition-all">
      {/* Header */}
      <div className="p-4">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center space-x-3">
            <div className={`w-10 h-10 rounded-xl ${roleConfig.bgColor} flex items-center justify-center`}>
              <span className={`text-sm font-bold ${roleConfig.color}`}>{stakeholder.roleType}</span>
            </div>
            <div className="min-w-0">
              <h4 className="text-sm font-semibold text-slate-900 truncate">{stakeholder.name}</h4>
              <p className="text-xs text-slate-500 truncate">{stakeholder.title}</p>
            </div>
          </div>
          {stakeholder.isNewHire && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
              New Hire
            </span>
          )}
        </div>

        {/* Contact Info */}
        <div className="flex items-center space-x-3 text-xs text-slate-500">
          {stakeholder.contact.email && (
            <a href={`mailto:${stakeholder.contact.email}`} className="hover:text-primary-600 truncate max-w-[150px]" title={stakeholder.contact.email}>
              <svg className="w-3 h-3 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              Email
            </a>
          )}
          {stakeholder.contact.linkedinUrl && (
            <a href={stakeholder.contact.linkedinUrl} target="_blank" rel="noopener noreferrer" className="hover:text-primary-600">
              <svg className="w-3 h-3 inline mr-1" fill="currentColor" viewBox="0 0 24 24">
                <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z" />
              </svg>
              LinkedIn
            </a>
          )}
          {stakeholder.contact.phone && (
            <a href={`tel:${stakeholder.contact.phone}`} className="hover:text-primary-600">
              <svg className="w-3 h-3 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
              </svg>
              Call
            </a>
          )}
        </div>
      </div>

      {/* Expandable Details */}
      {expanded && (
        <div className="px-4 pb-4 pt-2 border-t border-slate-100 space-y-3">
          {/* Bio */}
          {stakeholder.bio && (
            <div>
              <p className="text-xs font-medium text-slate-700 mb-1">Bio</p>
              <p className="text-xs text-slate-600 leading-relaxed">{stakeholder.bio}</p>
            </div>
          )}

          {/* Strategic Priorities */}
          {stakeholder.strategicPriorities && stakeholder.strategicPriorities.length > 0 && (
            <div>
              <p className="text-xs font-medium text-slate-700 mb-1">Strategic Priorities</p>
              <ul className="space-y-1">
                {stakeholder.strategicPriorities.map((priority, index) => (
                  <li key={index} className="text-xs text-slate-600 flex items-start">
                    <span className="text-primary-500 mr-1.5">•</span>
                    {priority}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Communication Preference */}
          {stakeholder.communicationPreference && (
            <div>
              <p className="text-xs font-medium text-slate-700 mb-1">Communication Style</p>
              <p className="text-xs text-slate-600">{stakeholder.communicationPreference}</p>
            </div>
          )}

          {/* Recommended Play */}
          {stakeholder.recommendedPlay && (
            <div className="bg-primary-50 rounded-lg p-3">
              <p className="text-xs font-medium text-primary-700 mb-1">Recommended Play</p>
              <p className="text-xs text-primary-600">{stakeholder.recommendedPlay}</p>
            </div>
          )}

          {/* Generate Outreach Button */}
          {onGenerateOutreach && (
            <button
              onClick={() => onGenerateOutreach(stakeholder.roleType, stakeholder.name)}
              className="w-full mt-2 inline-flex items-center justify-center px-4 py-2 rounded-lg text-sm font-medium text-white bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700 transition-all shadow-sm"
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
              Generate Outreach
            </button>
          )}
        </div>
      )}

      {/* Expand/Collapse Button */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-2 bg-slate-50 text-xs font-medium text-slate-600 hover:bg-slate-100 transition-colors flex items-center justify-center"
      >
        {expanded ? (
          <>
            <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
            </svg>
            Show Less
          </>
        ) : (
          <>
            <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
            View Details
          </>
        )}
      </button>
    </div>
  );
}

export default function StakeholderMapCard({ stakeholderMap, onGenerateOutreach }: StakeholderMapCardProps) {
  return (
    <div className="card p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Stakeholder Map</h2>
            <p className="text-sm text-slate-500">Key decision makers and influencers</p>
          </div>
        </div>
        {stakeholderMap.stakeholders.length > 0 && (
          <span className="text-sm text-slate-500">
            {stakeholderMap.stakeholders.length} executive{stakeholderMap.stakeholders.length !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Stakeholder Grid */}
      {stakeholderMap.stakeholders.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {stakeholderMap.stakeholders.map((stakeholder, index) => (
            <StakeholderCard
              key={`${stakeholder.name}-${index}`}
              stakeholder={stakeholder}
              onGenerateOutreach={onGenerateOutreach}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-8">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-slate-100 flex items-center justify-center">
            <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
          </div>
          <p className="text-sm font-medium text-slate-900 mb-1">No stakeholders found</p>
          <p className="text-xs text-slate-500">Executive contact data unavailable for this company</p>
        </div>
      )}
    </div>
  );
}
