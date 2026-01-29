'use client';

import { useState, useEffect } from 'react';
import type { OutreachContent, StakeholderRoleType } from '@/types';

interface OutreachGeneratorModalProps {
  isOpen: boolean;
  onClose: () => void;
  jobId: string;
  roleType: StakeholderRoleType;
  stakeholderName?: string;
}

type TabType = 'email' | 'linkedin' | 'call';

const tabConfig: Record<TabType, { label: string; icon: React.ReactNode }> = {
  email: {
    label: 'Email',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
      </svg>
    ),
  },
  linkedin: {
    label: 'LinkedIn',
    icon: (
      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
        <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z" />
      </svg>
    ),
  },
  call: {
    label: 'Call Script',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
      </svg>
    ),
  },
};

function CopyButton({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API failed
    }
  };

  return (
    <button
      onClick={handleCopy}
      className="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors"
    >
      {copied ? (
        <>
          <svg className="w-3.5 h-3.5 mr-1.5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          Copied!
        </>
      ) : (
        <>
          <svg className="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          Copy {label}
        </>
      )}
    </button>
  );
}

export default function OutreachGeneratorModal({
  isOpen,
  onClose,
  jobId,
  roleType,
  stakeholderName,
}: OutreachGeneratorModalProps) {
  const [activeTab, setActiveTab] = useState<TabType>('email');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [content, setContent] = useState<OutreachContent | null>(null);

  useEffect(() => {
    if (isOpen && !content) {
      generateContent();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  const generateContent = async () => {
    setLoading(true);
    setError(null);

    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/jobs/${jobId}/generate-outreach/${roleType}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          stakeholder_name: stakeholderName,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to generate outreach content');
      }

      const data = await response.json();
      setContent(data.content);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setContent(null);
    setError(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" onClick={handleClose} />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative w-full max-w-2xl bg-white rounded-2xl shadow-xl">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">Generate Outreach</h3>
              <p className="text-sm text-slate-500">
                {stakeholderName ? `For ${stakeholderName} (${roleType})` : `For ${roleType} role`}
              </p>
            </div>
            <button
              onClick={handleClose}
              className="p-2 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="p-6">
            {/* Loading State */}
            {loading && (
              <div className="text-center py-12">
                <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-primary-100 to-primary-50 flex items-center justify-center">
                  <svg className="w-8 h-8 text-primary-500 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                </div>
                <p className="text-sm font-medium text-slate-900">Generating personalized content...</p>
                <p className="text-xs text-slate-500 mt-1">This may take a few moments</p>
              </div>
            )}

            {/* Error State */}
            {error && (
              <div className="text-center py-12">
                <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-red-100 flex items-center justify-center">
                  <svg className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <p className="text-sm font-medium text-slate-900 mb-2">Generation Failed</p>
                <p className="text-xs text-slate-500 mb-4">{error}</p>
                <button
                  onClick={generateContent}
                  className="inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium text-white bg-primary-500 hover:bg-primary-600 transition-colors"
                >
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Retry
                </button>
              </div>
            )}

            {/* Content Display */}
            {content && !loading && !error && (
              <>
                {/* Tabs */}
                <div className="flex space-x-1 mb-6 bg-slate-100 rounded-xl p-1">
                  {(['email', 'linkedin', 'call'] as TabType[]).map((tab) => {
                    const config = tabConfig[tab];
                    const isActive = activeTab === tab;
                    return (
                      <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={`flex-1 inline-flex items-center justify-center px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                          isActive
                            ? 'bg-white text-slate-900 shadow-sm'
                            : 'text-slate-600 hover:text-slate-900'
                        }`}
                      >
                        <span className="mr-2">{config.icon}</span>
                        {config.label}
                      </button>
                    );
                  })}
                </div>

                {/* Email Tab */}
                {activeTab === 'email' && (
                  <div className="space-y-4">
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <label className="text-xs font-medium text-slate-700">Subject Line</label>
                        <CopyButton text={content.email.subject} label="Subject" />
                      </div>
                      <div className="bg-slate-50 rounded-xl p-4 text-sm text-slate-900">
                        {content.email.subject}
                      </div>
                    </div>
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <label className="text-xs font-medium text-slate-700">Email Body</label>
                        <CopyButton text={content.email.body} label="Body" />
                      </div>
                      <div className="bg-slate-50 rounded-xl p-4 text-sm text-slate-900 whitespace-pre-wrap max-h-64 overflow-y-auto">
                        {content.email.body}
                      </div>
                    </div>
                  </div>
                )}

                {/* LinkedIn Tab */}
                {activeTab === 'linkedin' && (
                  <div className="space-y-4">
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <label className="text-xs font-medium text-slate-700">Connection Request</label>
                        <CopyButton text={content.linkedin.connectionRequest} label="Message" />
                      </div>
                      <div className="bg-slate-50 rounded-xl p-4 text-sm text-slate-900 whitespace-pre-wrap">
                        {content.linkedin.connectionRequest}
                      </div>
                    </div>
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <label className="text-xs font-medium text-slate-700">Follow-up Message</label>
                        <CopyButton text={content.linkedin.followupMessage} label="Message" />
                      </div>
                      <div className="bg-slate-50 rounded-xl p-4 text-sm text-slate-900 whitespace-pre-wrap">
                        {content.linkedin.followupMessage}
                      </div>
                    </div>
                  </div>
                )}

                {/* Call Script Tab */}
                {activeTab === 'call' && (
                  <div className="space-y-4">
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <label className="text-xs font-medium text-slate-700">Opening</label>
                        <CopyButton text={content.callScript.opening} label="Opening" />
                      </div>
                      <div className="bg-slate-50 rounded-xl p-4 text-sm text-slate-900 whitespace-pre-wrap">
                        {content.callScript.opening}
                      </div>
                    </div>
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <label className="text-xs font-medium text-slate-700">Value Proposition</label>
                        <CopyButton text={content.callScript.valueProposition} label="Value Prop" />
                      </div>
                      <div className="bg-slate-50 rounded-xl p-4 text-sm text-slate-900 whitespace-pre-wrap">
                        {content.callScript.valueProposition}
                      </div>
                    </div>
                    <div>
                      <label className="text-xs font-medium text-slate-700 mb-2 block">Discovery Questions</label>
                      <div className="bg-slate-50 rounded-xl p-4 space-y-2">
                        {content.callScript.questions.map((question, index) => (
                          <div key={index} className="flex items-start text-sm">
                            <span className="text-primary-500 font-medium mr-2">{index + 1}.</span>
                            <span className="text-slate-900">{question}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <label className="text-xs font-medium text-slate-700">Closing CTA</label>
                        <CopyButton text={content.callScript.closingCTA} label="CTA" />
                      </div>
                      <div className="bg-slate-50 rounded-xl p-4 text-sm text-slate-900 whitespace-pre-wrap">
                        {content.callScript.closingCTA}
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Footer */}
          {content && !loading && !error && (
            <div className="flex items-center justify-between px-6 py-4 border-t border-slate-200 bg-slate-50 rounded-b-2xl">
              <p className="text-xs text-slate-500">
                Generated at {new Date(content.generatedAt).toLocaleString()}
              </p>
              <button
                onClick={generateContent}
                className="inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 transition-colors"
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Regenerate
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
