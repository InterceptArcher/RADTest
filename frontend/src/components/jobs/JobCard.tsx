'use client';

import Link from 'next/link';
import type { JobWithMetadata } from '@/types';

interface JobCardProps {
  job: JobWithMetadata;
}

const statusColors = {
  pending: 'bg-gray-100 text-gray-800',
  processing: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
};

const statusLabels = {
  pending: 'Pending',
  processing: 'Processing',
  completed: 'Completed',
  failed: 'Failed',
};

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (seconds < 60) return 'Just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} hr ago`;
  return `${Math.floor(seconds / 86400)} days ago`;
}

export default function JobCard({ job }: JobCardProps) {
  const isClickable = job.status === 'completed';

  const cardContent = (
    <div
      className={`bg-white rounded-xl border border-gray-200 p-5 transition-all ${
        isClickable
          ? 'hover:shadow-lg hover:border-blue-300 cursor-pointer'
          : 'opacity-90'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <span
          className={`px-2.5 py-1 rounded-full text-xs font-medium ${
            statusColors[job.status]
          }`}
        >
          {statusLabels[job.status]}
        </span>
        <span className="text-xs text-gray-500">
          {formatTimeAgo(job.createdAt)}
        </span>
      </div>

      {/* Company Info */}
      <h3 className="text-lg font-semibold text-gray-900 mb-1 truncate">
        {job.companyName}
      </h3>
      <p className="text-sm text-gray-500 mb-4 truncate">{job.domain}</p>

      {/* Progress */}
      {(job.status === 'pending' || job.status === 'processing') && (
        <div className="space-y-2">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-500"
              style={{ width: `${job.progress}%` }}
            />
          </div>
          <p className="text-xs text-gray-600 truncate">{job.currentStep}</p>
        </div>
      )}

      {/* Completed Info */}
      {job.status === 'completed' && job.result && (
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <svg
              className="w-4 h-4 text-green-500"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clipRule="evenodd"
              />
            </svg>
            <span className="text-sm text-gray-600">
              Confidence: {Math.round(job.result.confidence_score * 100)}%
            </span>
          </div>
          <svg
            className="w-5 h-5 text-gray-400"
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
        <div className="flex items-center space-x-2 text-red-600">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clipRule="evenodd"
            />
          </svg>
          <span className="text-sm">Processing failed</span>
        </div>
      )}
    </div>
  );

  if (isClickable) {
    return <Link href={`/dashboard/jobs/${job.jobId}`}>{cardContent}</Link>;
  }

  return cardContent;
}
