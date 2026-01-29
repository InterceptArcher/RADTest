'use client';

import { useState } from 'react';
import Link from 'next/link';
import type { JobWithMetadata } from '@/types';
import { useJobs } from '@/hooks/useJobs';

interface JobCardProps {
  job: JobWithMetadata;
}

const statusConfig = {
  pending: {
    bg: 'bg-slate-100',
    text: 'text-slate-700',
    ring: 'ring-slate-500/20',
    dot: 'bg-slate-400',
    label: 'Pending',
  },
  processing: {
    bg: 'bg-primary-50',
    text: 'text-primary-700',
    ring: 'ring-primary-600/20',
    dot: 'bg-primary-500',
    label: 'Processing',
  },
  completed: {
    bg: 'bg-emerald-50',
    text: 'text-emerald-700',
    ring: 'ring-emerald-600/20',
    dot: 'bg-emerald-500',
    label: 'Completed',
  },
  failed: {
    bg: 'bg-red-50',
    text: 'text-red-700',
    ring: 'ring-red-600/20',
    dot: 'bg-red-500',
    label: 'Failed',
  },
};

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (seconds < 60) return 'Just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export default function JobCard({ job }: JobCardProps) {
  const { removeJob } = useJobs();
  const [showConfirm, setShowConfirm] = useState(false);
  const isClickable = job.status === 'completed';
  const status = statusConfig[job.status];

  const handleDelete = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setShowConfirm(true);
  };

  const confirmDelete = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    removeJob(job.jobId);
    setShowConfirm(false);
  };

  const cancelDelete = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setShowConfirm(false);
  };

  const cardContent = (
    <div
      className={`card p-5 relative ${
        isClickable
          ? 'hover:border-primary-200 hover:shadow-glow cursor-pointer group'
          : 'group'
      }`}
    >
      {/* Delete Confirmation Overlay */}
      {showConfirm && (
        <div className="absolute inset-0 bg-white/95 backdrop-blur-sm rounded-2xl z-10 flex flex-col items-center justify-center p-4">
          <p className="text-sm font-medium text-slate-900 mb-3 text-center">Delete this job?</p>
          <div className="flex gap-2">
            <button
              onClick={cancelDelete}
              className="px-3 py-1.5 text-sm font-medium text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={confirmDelete}
              className="px-3 py-1.5 text-sm font-medium text-white bg-red-500 hover:bg-red-600 rounded-lg transition-colors"
            >
              Delete
            </button>
          </div>
        </div>
      )}

      {/* Delete Button */}
      <button
        onClick={handleDelete}
        className="absolute top-3 right-3 p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all z-[5]"
        title="Delete job"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
      </button>

      {/* Header */}
      <div className="flex items-center justify-between mb-4 pr-6">
        <span
          className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ring-1 ring-inset ${status.bg} ${status.text} ${status.ring}`}
        >
          {(job.status === 'processing' || job.status === 'pending') && (
            <span className={`w-1.5 h-1.5 rounded-full ${status.dot} mr-1.5 animate-pulse`} />
          )}
          {status.label}
        </span>
        <span className="text-xs text-slate-500 font-medium">
          {formatTimeAgo(job.createdAt)}
        </span>
      </div>

      {/* Company Info */}
      <h3 className="text-lg font-semibold text-slate-900 mb-1 truncate group-hover:text-primary-600 transition-colors">
        {job.companyName}
      </h3>
      <p className="text-sm text-slate-500 mb-4 truncate">{job.domain}</p>

      {/* Progress */}
      {(job.status === 'pending' || job.status === 'processing') && (
        <div className="space-y-2">
          <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-gradient-to-r from-primary-500 to-primary-400 h-1.5 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${job.progress}%` }}
            />
          </div>
          <p className="text-xs text-slate-600 truncate">{job.currentStep}</p>
        </div>
      )}

      {/* Completed Info */}
      {job.status === 'completed' && job.result && (
        <div className="flex items-center justify-between pt-2 border-t border-slate-100">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center">
              <svg
                className="w-4 h-4 text-emerald-600"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div>
              <p className="text-xs text-slate-500">Confidence</p>
              <p className="text-sm font-semibold text-emerald-600">
                {Math.round(job.result.confidence_score * 100)}%
              </p>
            </div>
          </div>
          <svg
            className="w-5 h-5 text-slate-400 group-hover:text-primary-500 group-hover:translate-x-0.5 transition-all"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5l7 7-7 7"
            />
          </svg>
        </div>
      )}

      {/* Failed Info */}
      {job.status === 'failed' && (
        <div className="flex items-center space-x-2 pt-2 border-t border-slate-100">
          <div className="w-8 h-8 rounded-lg bg-red-50 flex items-center justify-center">
            <svg className="w-4 h-4 text-red-600" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <span className="text-sm font-medium text-red-600">Processing failed</span>
        </div>
      )}
    </div>
  );

  if (isClickable && !showConfirm) {
    return <Link href={`/dashboard/jobs/${job.jobId}`}>{cardContent}</Link>;
  }

  return cardContent;
}
