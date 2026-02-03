'use client';

import { useState } from 'react';
import type { StakeholderMap, Stakeholder, StakeholderRoleType } from '@/types';

interface StakeholderMapCardProps {
  stakeholderMap: StakeholderMap;
  onGenerateOutreach?: (roleType: StakeholderRoleType, stakeholderName?: string) => void;
}

const roleTypeConfig: Record<StakeholderRoleType, { color: string; bgColor: string; description: string }> = {
  CIO: { color: 'text-blue-700', bgColor: 'bg-blue-100', description: 'Chief Information Officer' },
  CTO: { color: 'text-purple-700', bgColor: 'bg-purple-100', description: 'Chief Technology Officer' },
  CISO: { color: 'text-red-700', bgColor: 'bg-red-100', description: 'Chief Information Security Officer' },
  COO: { color: 'text-emerald-700', bgColor: 'bg-emerald-100', description: 'Chief Operating Officer' },
  CFO: { color: 'text-amber-700', bgColor: 'bg-amber-100', description: 'Chief Financial Officer' },
  CPO: { color: 'text-pink-700', bgColor: 'bg-pink-100', description: 'Chief Product Officer' },
  CEO: { color: 'text-indigo-700', bgColor: 'bg-indigo-100', description: 'Chief Executive Officer' },
  CMO: { color: 'text-orange-700', bgColor: 'bg-orange-100', description: 'Chief Marketing Officer' },
  VP: { color: 'text-teal-700', bgColor: 'bg-teal-100', description: 'Vice President' },
  Director: { color: 'text-cyan-700', bgColor: 'bg-cyan-100', description: 'Director' },
  Unknown: { color: 'text-slate-700', bgColor: 'bg-slate-100', description: 'Executive' },
};

interface StakeholderDetailCardProps {
  stakeholder: Stakeholder;
  onGenerateOutreach?: (roleType: StakeholderRoleType, stakeholderName?: string) => void;
}

function StakeholderDetailCard({ stakeholder, onGenerateOutreach }: StakeholderDetailCardProps) {
  if (!stakeholder) {
    return null;
  }

  const roleConfig = roleTypeConfig[stakeholder.roleType] || roleTypeConfig.Unknown;
  const contact = stakeholder.contact || {};
  const strategicPriorities = Array.isArray(stakeholder.strategicPriorities) ? stakeholder.strategicPriorities : [];

  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
      {/* Header */}
      <div className={`${roleConfig.bgColor} px-4 py-3 border-b border-slate-200`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className={`w-10 h-10 rounded-xl bg-white/80 flex items-center justify-center`}>
              <span className={`text-sm font-bold ${roleConfig.color}`}>{stakeholder.roleType}</span>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-slate-900">{stakeholder.name}</h4>
              <p className="text-xs text-slate-600">{stakeholder.title}</p>
            </div>
          </div>
          {stakeholder.isNewHire && (
            <div className="flex items-center space-x-1 bg-emerald-500 text-white px-2 py-1 rounded-full">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              <span className="text-[10px] font-medium">New Hire</span>
            </div>
          )}
        </div>
        {stakeholder.isNewHire && stakeholder.hireDate && (
          <p className="text-xs text-slate-600 mt-2">Started: {stakeholder.hireDate}</p>
        )}
      </div>

      <div className="p-4 space-y-4">
        {/* Bio */}
        <div>
          <h5 className="text-xs font-semibold text-slate-700 mb-2 uppercase tracking-wide">Bio</h5>
          <p className="text-sm text-slate-600 leading-relaxed">
            {stakeholder.bio || `${stakeholder.name} serves as ${stakeholder.title}, responsible for key strategic initiatives and organizational leadership.`}
          </p>
        </div>

        {/* Contact Info */}
        <div>
          <h5 className="text-xs font-semibold text-slate-700 mb-2 uppercase tracking-wide">Contact Information</h5>
          <div className="grid grid-cols-1 gap-2">
            {contact.email && (
              <a
                href={`mailto:${contact.email}`}
                className="flex items-center text-sm text-primary-600 hover:text-primary-700"
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                {contact.email}
              </a>
            )}
            {contact.phone && (
              <a
                href={`tel:${contact.phone}`}
                className="flex items-center text-sm text-primary-600 hover:text-primary-700"
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                </svg>
                {contact.phone}
              </a>
            )}
            {contact.linkedinUrl && (
              <a
                href={contact.linkedinUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center text-sm text-primary-600 hover:text-primary-700"
              >
                <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z" />
                </svg>
                LinkedIn Profile
              </a>
            )}
            {!contact.email && !contact.phone && !contact.linkedinUrl && (
              <p className="text-sm text-slate-400">Contact information not available</p>
            )}
          </div>
        </div>

        {/* Strategic Priorities */}
        {strategicPriorities.length > 0 && (
          <div>
            <h5 className="text-xs font-semibold text-slate-700 mb-2 uppercase tracking-wide">Strategic Priorities</h5>
            <ul className="space-y-1.5">
              {strategicPriorities.map((priority, index) => {
                const priorityText = typeof priority === 'string' ? priority : priority.priority;
                const priorityDescription = typeof priority === 'object' && priority.description ? priority.description : null;
                return (
                  <li key={index} className="flex items-start text-sm text-slate-600">
                    <span className="w-5 h-5 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center text-xs font-bold mr-2 flex-shrink-0 mt-0.5">
                      {index + 1}
                    </span>
                    <div>
                      <span>{priorityText}</span>
                      {priorityDescription && (
                        <p className="text-xs text-slate-500 mt-0.5">{priorityDescription}</p>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        {/* Communication Preference */}
        {stakeholder.communicationPreference && (
          <div>
            <h5 className="text-xs font-semibold text-slate-700 mb-2 uppercase tracking-wide">Communication Preference</h5>
            <p className="text-sm text-slate-600">{stakeholder.communicationPreference}</p>
          </div>
        )}

        {/* Recommended Play */}
        {stakeholder.recommendedPlay && (
          <div className="bg-primary-50 rounded-lg p-3">
            <h5 className="text-xs font-semibold text-primary-700 mb-1 uppercase tracking-wide">Recommended Play</h5>
            <p className="text-sm text-primary-900">{stakeholder.recommendedPlay}</p>
          </div>
        )}

        {/* Generate Outreach Button */}
        {onGenerateOutreach && (
          <button
            onClick={() => onGenerateOutreach(stakeholder.roleType, stakeholder.name)}
            className="w-full inline-flex items-center justify-center px-4 py-2.5 rounded-lg text-sm font-medium text-white bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700 transition-all shadow-sm"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
            </svg>
            Generate Personalized Outreach
          </button>
        )}
      </div>
    </div>
  );
}

export default function StakeholderMapCard({ stakeholderMap, onGenerateOutreach }: StakeholderMapCardProps) {
  const [expanded, setExpanded] = useState(false);

  // Null safety for stakeholder map data
  if (!stakeholderMap) {
    return null;
  }

  const stakeholders = Array.isArray(stakeholderMap.stakeholders) ? stakeholderMap.stakeholders : [];
  const stakeholderCount = stakeholders.length;

  // Get preview stakeholders (first 3)
  const previewStakeholders = stakeholders.slice(0, 3);

  return (
    <div className="card overflow-hidden">
      {/* Clickable Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-6 text-left hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center justify-between">
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
          <div className="flex items-center space-x-3">
            {stakeholderCount > 0 && (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 ring-1 ring-inset ring-indigo-600/20">
                {stakeholderCount} Executive{stakeholderCount !== 1 ? 's' : ''}
              </span>
            )}
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
        {!expanded && stakeholderCount > 0 && (
          <div className="mt-4 flex flex-wrap gap-3">
            {previewStakeholders.map((stakeholder, index) => {
              const roleConfig = roleTypeConfig[stakeholder.roleType] || roleTypeConfig.Unknown;
              return (
                <div
                  key={index}
                  className="flex items-center space-x-2 bg-slate-50 rounded-lg px-3 py-2"
                >
                  <div className={`w-8 h-8 rounded-lg ${roleConfig.bgColor} flex items-center justify-center`}>
                    <span className={`text-xs font-bold ${roleConfig.color}`}>{stakeholder.roleType}</span>
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-slate-900 truncate">{stakeholder.name}</p>
                    <p className="text-xs text-slate-500 truncate">{stakeholder.title}</p>
                  </div>
                </div>
              );
            })}
            {stakeholderCount > 3 && (
              <div className="flex items-center text-xs text-slate-500">
                +{stakeholderCount - 3} more
              </div>
            )}
          </div>
        )}
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="px-6 pb-6 border-t border-slate-100">
          <div className="mt-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-slate-900 flex items-center">
                <svg className="w-4 h-4 mr-2 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
                Executive Profiles
              </h3>
              <p className="text-xs text-slate-500">
                Target roles: CIO, CTO, CISO, COO, CFO, CPO
              </p>
            </div>

            {stakeholderCount > 0 ? (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {stakeholders.map((stakeholder, index) => (
                  <StakeholderDetailCard
                    key={`${stakeholder.name}-${index}`}
                    stakeholder={stakeholder}
                    onGenerateOutreach={onGenerateOutreach}
                  />
                ))}
              </div>
            ) : (
              <div className="bg-slate-50 rounded-xl p-8 text-center">
                <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-slate-100 flex items-center justify-center">
                  <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                </div>
                <p className="text-sm font-medium text-slate-900 mb-1">No stakeholders found</p>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  Executive contact data unavailable for this company. We searched for CIO, CTO, CISO, COO, CFO, and CPO roles.
                </p>
              </div>
            )}

            {/* Data Source Note */}
            <div className="mt-6 flex items-start space-x-2 text-xs text-slate-500 bg-slate-50 rounded-lg p-3">
              <svg className="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p>Stakeholder data sourced from Apollo.io. Bios, priorities, and recommendations are AI-generated based on role and company context. New hire status detected from employment history.</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
