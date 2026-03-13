'use client';

import Link from 'next/link';
import AddCompanyForm from '@/components/jobs/AddCompanyForm';
import NetworkDocs from '@/components/ui/NetworkDocs';
import { useJobs, useJobPolling } from '@/hooks/useJobs';
import { useSellers } from '@/hooks/useSellers';

const statusDisplay: Record<string, { bg: string; text: string; dot?: string; label: string }> = {
  pending: { bg: 'bg-slate-100', text: 'text-slate-600', dot: 'bg-slate-400', label: 'Pending' },
  processing: { bg: 'bg-blue-50', text: 'text-blue-700', dot: 'bg-blue-500', label: 'Processing' },
  completed: { bg: 'bg-emerald-50', text: 'text-emerald-700', label: 'Completed' },
  failed: { bg: 'bg-red-50', text: 'text-red-700', label: 'Failed' },
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

export default function DashboardHome() {
  const { jobs } = useJobs();
  useJobPolling();
  const { sellers, sellerJobs, getMonthlyJobCount } = useSellers();

  const completedCount = jobs.filter((j) => j.status === 'completed').length;
  const processingCount = jobs.filter((j) => j.status === 'processing' || j.status === 'pending').length;
  const failedCount = jobs.filter((j) => j.status === 'failed').length;
  const completionRate = jobs.length > 0 ? Math.round((completedCount / jobs.length) * 100) : 0;

  const MONTHLY_LIMIT = 40;

  return (
    <div className="p-6 lg:p-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-[#282727]">Company Intelligence</h1>
        <p className="text-base text-[#939393]">Generate comprehensive company profiles powered by 20 AI specialists.</p>
      </div>

      {/* Stats Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="card px-5 py-3.5">
          <p className="text-sm text-[#939393] mb-0.5">Total Jobs</p>
          <p className="text-3xl font-bold text-[#282727]">{jobs.length}</p>
        </div>
        <div className="card px-5 py-3.5">
          <div className="flex items-baseline justify-between">
            <div>
              <p className="text-sm text-[#939393] mb-0.5">Completed</p>
              <p className="text-3xl font-bold text-emerald-600">{completedCount}</p>
            </div>
            {jobs.length > 0 && (
              <span className="text-sm font-medium text-emerald-600">{completionRate}%</span>
            )}
          </div>
        </div>
        <div className="card px-5 py-3.5">
          <p className="text-sm text-[#939393] mb-0.5">Processing</p>
          <div className="flex items-center space-x-2">
            <p className="text-3xl font-bold text-blue-600">{processingCount}</p>
            {processingCount > 0 && (
              <span className="w-2.5 h-2.5 bg-blue-500 rounded-full animate-pulse" />
            )}
          </div>
        </div>
        <div className="card px-5 py-3.5">
          <p className="text-sm text-[#939393] mb-0.5">Failed</p>
          <p className="text-3xl font-bold text-red-600">{failedCount}</p>
        </div>
      </div>

      {/* Main content: Form + Activity Table — same height */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-stretch">
        {/* Form Column */}
        <div className="xl:col-span-4 flex">
          <div className="card p-5 flex flex-col w-full">
            <h2 className="text-base font-semibold text-[#282727] mb-3">New Profile</h2>
            <AddCompanyForm />
          </div>
        </div>

        {/* Activity Table Column */}
        <div className="xl:col-span-8 flex">
          <div className="card overflow-hidden flex flex-col w-full">
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
              <h2 className="text-base font-semibold text-[#282727]">Recent Activity</h2>
              {jobs.length > 0 && (
                <Link
                  href="/dashboard/jobs"
                  className="text-sm font-medium text-primary-500 hover:text-primary-600"
                >
                  View all →
                </Link>
              )}
            </div>

            {jobs.length === 0 ? (
              <div className="text-center py-12 px-4 flex-1 flex flex-col items-center justify-center">
                <div className="w-14 h-14 mx-auto mb-3 rounded-lg bg-slate-100 flex items-center justify-center">
                  <svg className="w-7 h-7 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                </div>
                <p className="text-base font-medium text-[#282727] mb-1">No jobs yet</p>
                <p className="text-sm text-[#939393]">Add a company using the form to get started.</p>
              </div>
            ) : (
              <div className="flex-1 flex flex-col">
                {/* Table header */}
                <div className="hidden sm:grid grid-cols-12 gap-3 px-5 py-2.5 bg-slate-50 text-xs font-semibold text-[#939393] uppercase tracking-wider border-b border-slate-100">
                  <div className="col-span-4">Company</div>
                  <div className="col-span-2">Status</div>
                  <div className="col-span-2">Seller</div>
                  <div className="col-span-2">Confidence</div>
                  <div className="col-span-2 text-right">Time</div>
                </div>

                {/* Table rows */}
                <div className="flex-1">
                  {jobs.slice(0, 12).map((job) => {
                    const status = statusDisplay[job.status] || statusDisplay.pending;
                    const isClickable = job.status === 'completed';

                    const row = (
                      <div
                        className={`grid grid-cols-1 sm:grid-cols-12 gap-1 sm:gap-3 px-5 py-3 border-b border-slate-50 items-center transition-colors ${
                          isClickable ? 'hover:bg-slate-50 cursor-pointer group' : ''
                        }`}
                      >
                        {/* Company */}
                        <div className="sm:col-span-4 min-w-0">
                          <p className={`text-sm font-medium text-[#282727] truncate ${isClickable ? 'group-hover:text-primary-500' : ''}`}>
                            {job.companyName}
                          </p>
                          <p className="text-xs text-[#939393] truncate">{job.domain}</p>
                        </div>
                        {/* Status */}
                        <div className="sm:col-span-2">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${status.bg} ${status.text}`}>
                            {status.dot && (
                              <span className={`w-1.5 h-1.5 rounded-full ${status.dot} mr-1 animate-pulse`} />
                            )}
                            {status.label}
                          </span>
                        </div>
                        {/* Seller */}
                        <div className="sm:col-span-2">
                          {job.sellerName ? (
                            <span className="text-sm text-[#282727]">{job.sellerName}</span>
                          ) : (
                            <span className="text-sm text-slate-300">—</span>
                          )}
                        </div>
                        {/* Confidence */}
                        <div className="sm:col-span-2">
                          {job.status === 'completed' && job.result ? (
                            <span className="text-sm font-semibold text-emerald-600">
                              {Math.round(job.result.confidence_score * 100)}%
                            </span>
                          ) : job.status === 'processing' || job.status === 'pending' ? (
                            <div className="w-16 bg-slate-100 rounded-full h-1.5">
                              <div
                                className="bg-blue-500 h-1.5 rounded-full transition-all"
                                style={{ width: `${job.progress}%` }}
                              />
                            </div>
                          ) : (
                            <span className="text-sm text-slate-300">—</span>
                          )}
                        </div>
                        {/* Time */}
                        <div className="sm:col-span-2 text-right flex items-center justify-end space-x-2">
                          <span className="text-xs text-[#939393]">{formatTimeAgo(job.createdAt)}</span>
                          {isClickable && (
                            <svg className="w-4 h-4 text-slate-300 group-hover:text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                            </svg>
                          )}
                        </div>
                      </div>
                    );

                    if (isClickable) {
                      return <Link key={job.jobId} href={`/dashboard/jobs/${job.jobId}`}>{row}</Link>;
                    }
                    return <div key={job.jobId}>{row}</div>;
                  })}
                </div>

                {/* Show count if more jobs */}
                {jobs.length > 12 && (
                  <div className="px-5 py-3 text-center border-t border-slate-100 mt-auto">
                    <Link href="/dashboard/jobs" className="text-sm font-medium text-primary-500 hover:text-primary-600">
                      View all {jobs.length} jobs →
                    </Link>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Sellers Overview Card */}
      {sellers.length > 0 && (
        <div className="mt-6">
          <div className="card overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h2 className="text-base font-semibold text-[#282727]">Sellers Overview</h2>
              <Link
                href="/dashboard/sellers"
                className="text-sm font-medium text-primary-500 hover:text-primary-600"
              >
                Manage sellers →
              </Link>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-px bg-slate-100">
              {sellers.map((seller) => {
                const monthlyCount = getMonthlyJobCount(seller.id);
                const sellerJobsList = sellerJobs.filter((j) => j.seller_id === seller.id);
                const completedSellerJobs = sellerJobsList.filter((j) => j.status === 'completed').length;
                const usagePercent = Math.min((monthlyCount / MONTHLY_LIMIT) * 100, 100);
                const isOverLimit = monthlyCount >= MONTHLY_LIMIT;

                return (
                  <Link key={seller.id} href={`/dashboard/sellers/${seller.id}`}>
                    <div className="bg-white p-4 hover:bg-slate-50 transition-colors cursor-pointer h-full">
                      <div className="flex items-center space-x-2.5 mb-2.5">
                        <div className="w-8 h-8 rounded bg-[#282727] flex items-center justify-center flex-shrink-0">
                          <span className="text-white font-bold text-sm">{seller.name.charAt(0)}</span>
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-semibold text-[#282727] truncate">{seller.name}</p>
                          <p className="text-xs text-[#939393]">{sellerJobsList.length} job{sellerJobsList.length !== 1 ? 's' : ''}</p>
                        </div>
                      </div>
                      <div className="mb-2">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs text-[#939393]">Monthly</span>
                          <span className={`text-xs font-semibold ${isOverLimit ? 'text-red-600' : monthlyCount >= 30 ? 'text-amber-600' : 'text-[#282727]'}`}>
                            {monthlyCount}/{MONTHLY_LIMIT}
                          </span>
                        </div>
                        <div className="w-full bg-slate-100 rounded-full h-1.5">
                          <div
                            className={`h-1.5 rounded-full transition-all ${isOverLimit ? 'bg-red-500' : monthlyCount >= 30 ? 'bg-amber-500' : 'bg-[#282727]'}`}
                            style={{ width: `${usagePercent}%` }}
                          />
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        {completedSellerJobs > 0 && (
                          <span className="flex items-center text-xs text-emerald-600">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1" />{completedSellerJobs} done
                          </span>
                        )}
                        {sellerJobsList.length === 0 && (
                          <span className="text-xs text-slate-300">No jobs yet</span>
                        )}
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Platform Documentation Network */}
      <div className="mt-6">
        <NetworkDocs />
      </div>
    </div>
  );
}
