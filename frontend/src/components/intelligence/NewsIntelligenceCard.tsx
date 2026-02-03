'use client';

import { useState } from 'react';
import type { NewsIntelligence } from '@/types';

interface NewsIntelligenceCardProps {
  newsIntelligence: NewsIntelligence;
  companyName: string;
}

const newsCategoryConfig = {
  executiveChanges: {
    label: 'Executive Changes',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
      </svg>
    ),
    bg: 'bg-blue-50',
    text: 'text-blue-700',
    border: 'border-blue-200',
  },
  funding: {
    label: 'Funding',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    bg: 'bg-green-50',
    text: 'text-green-700',
    border: 'border-green-200',
  },
  partnerships: {
    label: 'Partnerships & M&A',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
      </svg>
    ),
    bg: 'bg-purple-50',
    text: 'text-purple-700',
    border: 'border-purple-200',
  },
  expansions: {
    label: 'Expansions',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    bg: 'bg-amber-50',
    text: 'text-amber-700',
    border: 'border-amber-200',
  },
};

function isNoDataMessage(text: string): boolean {
  if (!text) return true;
  const noDataIndicators = [
    'no recent',
    'no news',
    'not available',
    'not found',
    'none found',
    'no data'
  ];
  return noDataIndicators.some(indicator => text.toLowerCase().includes(indicator));
}

export default function NewsIntelligenceCard({
  newsIntelligence,
  companyName,
}: NewsIntelligenceCardProps) {
  const [expanded, setExpanded] = useState(false);

  if (!newsIntelligence) {
    return null;
  }

  const categories = [
    { key: 'executiveChanges', value: newsIntelligence.executiveChanges },
    { key: 'funding', value: newsIntelligence.funding },
    { key: 'partnerships', value: newsIntelligence.partnerships },
    { key: 'expansions', value: newsIntelligence.expansions },
  ];

  const hasNews = categories.some(cat => !isNoDataMessage(cat.value));
  const newsCount = newsIntelligence.articlesCount || 0;

  return (
    <div className="card overflow-hidden">
      {/* Clickable Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-6 text-left hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-rose-500 to-orange-500 flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900">News Intelligence</h2>
              <p className="text-sm text-slate-500">Recent company news and events</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            {newsCount > 0 && (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-rose-50 text-rose-700 ring-1 ring-inset ring-rose-600/20">
                {newsCount} articles
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
        {!expanded && (
          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
            {categories.map(({ key, value }) => {
              const config = newsCategoryConfig[key as keyof typeof newsCategoryConfig];
              const hasData = !isNoDataMessage(value);
              return (
                <div
                  key={key}
                  className={`rounded-lg p-3 ${hasData ? config.bg : 'bg-slate-50'}`}
                >
                  <div className={`flex items-center space-x-1 mb-1 ${hasData ? config.text : 'text-slate-400'}`}>
                    {config.icon}
                    <p className="text-xs font-medium">{config.label}</p>
                  </div>
                  <p className={`text-xs truncate ${hasData ? config.text : 'text-slate-400'}`}>
                    {hasData ? 'News found' : 'No recent news'}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="px-6 pb-6 border-t border-slate-100">
          {/* Date Range Info */}
          <div className="mt-4 flex items-center justify-between text-sm">
            <span className="text-slate-500">
              Showing news from: <span className="font-medium text-slate-700">{newsIntelligence.dateRange || 'Last 90 days'}</span>
            </span>
            {newsIntelligence.lastUpdated && (
              <span className="text-slate-400 text-xs">
                Last updated: {new Date(newsIntelligence.lastUpdated).toLocaleDateString()}
              </span>
            )}
          </div>

          {/* News Categories */}
          <div className="mt-6 space-y-4">
            {categories.map(({ key, value }) => {
              const config = newsCategoryConfig[key as keyof typeof newsCategoryConfig];
              const hasData = !isNoDataMessage(value);

              return (
                <div
                  key={key}
                  className={`rounded-xl p-4 border ${hasData ? `${config.bg} ${config.border}` : 'bg-slate-50 border-slate-200'}`}
                >
                  <div className={`flex items-center space-x-2 mb-2 ${hasData ? config.text : 'text-slate-500'}`}>
                    {config.icon}
                    <h3 className="text-sm font-semibold">{config.label}</h3>
                  </div>
                  <p className={`text-sm leading-relaxed ${hasData ? 'text-slate-700' : 'text-slate-400'}`}>
                    {value || 'No recent news found'}
                  </p>
                </div>
              );
            })}
          </div>

          {/* No News State */}
          {!hasNews && (
            <div className="mt-6 bg-slate-50 rounded-xl p-6 text-center">
              <svg className="w-8 h-8 mx-auto text-slate-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
              </svg>
              <p className="text-sm text-slate-500">No significant news found for {companyName}</p>
              <p className="text-xs text-slate-400 mt-1">We continuously monitor for new developments</p>
            </div>
          )}

          {/* Data Source Note */}
          <div className="mt-6 flex items-start space-x-2 text-xs text-slate-500 bg-slate-50 rounded-lg p-3">
            <svg className="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p>News data sourced from GNews API. Articles are categorized by type and filtered for relevance to {companyName}.</p>
          </div>
        </div>
      )}
    </div>
  );
}
