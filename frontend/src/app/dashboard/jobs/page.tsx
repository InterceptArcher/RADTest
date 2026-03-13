'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useJobs, useJobPolling } from '@/hooks/useJobs';

type FilterStatus = 'all' | 'processing' | 'completed' | 'failed';

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  if (seconds < 60) return 'Just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

const statusDisplay: Record<string, { bg: string; text: string; dot?: string; label: string }> = {
  pending: { bg: 'bg-slate-100', text: 'text-slate-600', dot: 'bg-slate-400', label: 'Pending' },
  processing: { bg: 'bg-blue-50', text: 'text-blue-700', dot: 'bg-blue-500', label: 'Processing' },
  completed: { bg: 'bg-emerald-50', text: 'text-emerald-700', label: 'Completed' },
  failed: { bg: 'bg-red-50', text: 'text-red-700', label: 'Failed' },
};

export default function JobsPage() {
  const { jobs, removeJob } = useJobs();
  useJobPolling();

  const [filter, setFilter] = useState<FilterStatus>('all');
  const [search, setSearch] = useState('');
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  const filteredJobs = (filter === 'all'
    ? jobs
    : jobs.filter((job) => filter === 'processing'
        ? (job.status === 'processing' || job.status === 'pending')
        : job.status === filter
      )
  ).filter((job) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return job.companyName.toLowerCase().includes(q) || job.domain.toLowerCase().includes(q);
  });

  const statusCounts = {
    all: jobs.length,
    processing: jobs.filter((j) => j.status === 'processing' || j.status === 'pending').length,
    completed: jobs.filter((j) => j.status === 'completed').length,
    failed: jobs.filter((j) => j.status === 'failed').length,
  };

  const filters: { key: FilterStatus; label: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'processing', label: 'Processing' },
    { key: 'completed', label: 'Completed' },
    { key: 'failed', label: 'Failed' },
  ];

  return (
    <div className="p-6 lg:p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-[#282727]">Job Queue</h1>
          <p className="text-base text-[#939393]">Monitor and manage your company profile requests.</p>
        </div>
        <Link href="/dashboard" className="btn-primary hidden sm:inline-flex text-sm">
          <svg className="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
          </svg>
          New Profile
        </Link>
      </div>

      {/* Search */}
      <div className="mb-4">
        <div className="relative">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#939393]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search companies by name or domain..."
            className="input-field pl-10"
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[#939393] hover:text-[#282727]"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-1 mb-4">
        {filters.map(({ key, label }) => {
          const isActive = filter === key;
          return (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? 'bg-[#282727] text-white'
                  : 'text-[#939393] hover:bg-white hover:text-[#282727]'
              }`}
            >
              {label}
              <span className={`ml-1.5 ${isActive ? 'text-white/60' : 'text-slate-400'}`}>
                {statusCounts[key]}
              </span>
            </button>
          );
        })}
      </div>

      {/* Table */}
      {filteredJobs.length === 0 ? (
        <div className="card p-12 text-center">
          <div className="w-12 h-12 mx-auto mb-3 rounded-lg bg-slate-100 flex items-center justify-center">
            <svg className="w-6 h-6 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h3 className="text-sm font-semibold text-[#282727] mb-1">
            {filter === 'all' ? 'No jobs yet' : `No ${filter} jobs`}
          </h3>
          <p className="text-xs text-[#939393] max-w-xs mx-auto mb-4">
            {filter === 'all'
              ? 'Start by adding a company to generate your first intelligence profile.'
              : 'There are no jobs with this status at the moment.'}
          </p>
          {filter === 'all' && (
            <Link href="/dashboard" className="btn-primary text-sm">Add Company</Link>
          )}
        </div>
      ) : (
        <div className="card overflow-hidden">
          {/* Table header */}
          <div className="hidden sm:grid grid-cols-12 gap-3 px-4 py-2 bg-slate-50 text-xs font-semibold text-[#939393] uppercase tracking-wider border-b border-slate-100">
            <div className="col-span-3">Company</div>
            <div className="col-span-2">Domain</div>
            <div className="col-span-1">Status</div>
            <div className="col-span-2">Seller</div>
            <div className="col-span-1">Confidence</div>
            <div className="col-span-1">Created</div>
            <div className="col-span-2 text-right">Actions</div>
          </div>

          {/* Table rows */}
          {filteredJobs.map((job) => {
            const status = statusDisplay[job.status] || statusDisplay.pending;
            const isClickable = job.status === 'completed';
            const isDeleting = deleteConfirmId === job.jobId;

            return (
              <div key={job.jobId} className="relative">
                {/* Delete confirmation overlay */}
                {isDeleting && (
                  <div className="absolute inset-0 bg-white/95 z-10 flex items-center justify-center gap-3">
                    <span className="text-xs font-medium text-[#282727]">Delete this job?</span>
                    <button
                      onClick={() => setDeleteConfirmId(null)}
                      className="px-2.5 py-1 text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-md"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => { removeJob(job.jobId); setDeleteConfirmId(null); }}
                      className="px-2.5 py-1 text-xs font-medium text-white bg-red-500 hover:bg-red-600 rounded-md"
                    >
                      Delete
                    </button>
                  </div>
                )}

                {isClickable ? (
                  <Link href={`/dashboard/jobs/${job.jobId}`}>
                    <div className="grid grid-cols-1 sm:grid-cols-12 gap-1 sm:gap-3 px-4 py-2.5 border-b border-slate-50 items-center hover:bg-slate-50 cursor-pointer group">
                      <div className="sm:col-span-3 min-w-0">
                        <p className="text-sm font-medium text-[#282727] truncate group-hover:text-primary-500">{job.companyName}</p>
                      </div>
                      <div className="sm:col-span-2 min-w-0">
                        <p className="text-xs text-[#939393] truncate">{job.domain}</p>
                      </div>
                      <div className="sm:col-span-1">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${status.bg} ${status.text}`}>
                          {status.dot && <span className={`w-1.5 h-1.5 rounded-full ${status.dot} mr-1 animate-pulse`} />}
                          {status.label}
                        </span>
                      </div>
                      <div className="sm:col-span-2 min-w-0">
                        {job.sellerName ? (
                          <span className="text-xs text-[#282727] truncate">{job.sellerName}</span>
                        ) : (
                          <span className="text-xs text-slate-300">—</span>
                        )}
                      </div>
                      <div className="sm:col-span-1">
                        {job.result ? (
                          <span className="text-xs font-semibold text-emerald-600">{Math.round(job.result.confidence_score * 100)}%</span>
                        ) : (
                          <span className="text-xs text-slate-300">—</span>
                        )}
                      </div>
                      <div className="sm:col-span-1">
                        <span className="text-xs text-[#939393]">{formatTimeAgo(job.createdAt)}</span>
                      </div>
                      <div className="sm:col-span-2 flex items-center justify-end space-x-2">
                        <button
                          onClick={(e) => { e.preventDefault(); e.stopPropagation(); setDeleteConfirmId(job.jobId); }}
                          className="p-1 rounded text-slate-300 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                        <svg className="w-3.5 h-3.5 text-slate-300 group-hover:text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </div>
                    </div>
                  </Link>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-12 gap-1 sm:gap-3 px-4 py-2.5 border-b border-slate-50 items-center group">
                    <div className="sm:col-span-3 min-w-0">
                      <p className="text-sm font-medium text-[#282727] truncate">{job.companyName}</p>
                    </div>
                    <div className="sm:col-span-2 min-w-0">
                      <p className="text-xs text-[#939393] truncate">{job.domain}</p>
                    </div>
                    <div className="sm:col-span-1">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${status.bg} ${status.text}`}>
                        {status.dot && <span className={`w-1.5 h-1.5 rounded-full ${status.dot} mr-1 animate-pulse`} />}
                        {status.label}
                      </span>
                    </div>
                    <div className="sm:col-span-2 min-w-0">
                      {job.sellerName ? (
                        <span className="text-xs text-[#282727] truncate">{job.sellerName}</span>
                      ) : (
                        <span className="text-xs text-slate-300">—</span>
                      )}
                    </div>
                    <div className="sm:col-span-1">
                      {(job.status === 'processing' || job.status === 'pending') ? (
                        <div className="w-12 bg-slate-100 rounded-full h-1">
                          <div className="bg-blue-500 h-1 rounded-full transition-all" style={{ width: `${job.progress}%` }} />
                        </div>
                      ) : (
                        <span className="text-xs text-slate-300">—</span>
                      )}
                    </div>
                    <div className="sm:col-span-1">
                      <span className="text-xs text-[#939393]">{formatTimeAgo(job.createdAt)}</span>
                    </div>
                    <div className="sm:col-span-2 flex items-center justify-end">
                      <button
                        onClick={() => setDeleteConfirmId(job.jobId)}
                        className="p-1 rounded text-slate-300 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
