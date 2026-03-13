'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useSellers } from '@/hooks/useSellers';
import { useJobs } from '@/hooks/useJobs';
import { groupJobsByMonth, getSalespersonBreakdown, getIndustryBreakdown } from '../helpers';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

const MONTHLY_LIMIT = 40;

const CHART_COLORS = ['#2563eb', '#059669', '#d97706', '#E02B23', '#7c3aed', '#0891b2', '#e11d48', '#ea580c'];

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function formatMonthLabel(key: string): string {
  const [year, month] = key.split('-');
  const date = new Date(Number(year), Number(month) - 1);
  return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
}

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (seconds < 60) return 'Just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

const statusConfig: Record<string, { bg: string; text: string; ring: string; dot: string; label: string }> = {
  pending: { bg: 'bg-slate-100', text: 'text-slate-700', ring: 'ring-slate-500/20', dot: 'bg-slate-400', label: 'Pending' },
  processing: { bg: 'bg-blue-50', text: 'text-blue-700', ring: 'ring-blue-600/20', dot: 'bg-blue-500', label: 'Processing' },
  completed: { bg: 'bg-emerald-50', text: 'text-emerald-700', ring: 'ring-emerald-600/20', dot: 'bg-emerald-500', label: 'Completed' },
  failed: { bg: 'bg-red-50', text: 'text-red-700', ring: 'ring-red-600/20', dot: 'bg-red-500', label: 'Failed' },
};

/* Custom chart tooltip */
function ChartTooltip({ active, payload }: any) {
  if (active && payload && payload.length) {
    return (
      <div className="bg-slate-900 text-white px-3 py-2 rounded-lg text-sm shadow-lg border border-slate-700">
        <p className="font-medium">{payload[0].payload.fullName || payload[0].payload.name || payload[0].name}</p>
        <p className="text-slate-300 mt-0.5">{payload[0].value} {payload[0].value === 1 ? 'job' : 'jobs'}</p>
      </div>
    );
  }
  return null;
}

export default function SellerDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { sellers, sellerJobs, getMonthlyJobCount } = useSellers();
  const { removeJob } = useJobs();
  const [deleteConfirmJobId, setDeleteConfirmJobId] = useState<string | null>(null);

  const sellerId = params.sellerId as string;
  const seller = sellers.find((s) => s.id === sellerId);
  const jobs = sellerJobs.filter((j) => j.seller_id === sellerId);
  const monthlyCount = getMonthlyJobCount(sellerId);
  const usagePercent = Math.min((monthlyCount / MONTHLY_LIMIT) * 100, 100);
  const isOverLimit = monthlyCount >= MONTHLY_LIMIT;

  const completedCount = jobs.filter((j) => j.status === 'completed').length;
  const processingCount = jobs.filter((j) => j.status === 'processing' || j.status === 'pending').length;
  const failedCount = jobs.filter((j) => j.status === 'failed').length;

  // Metrics
  const salespersonBreakdown = getSalespersonBreakdown(jobs);
  const industryBreakdown = getIndustryBreakdown(jobs);
  const monthGrouped = groupJobsByMonth(jobs);

  // Domain breakdown (top 5 most requested domains)
  const domainCounts = new Map<string, number>();
  for (const job of jobs) {
    domainCounts.set(job.domain, (domainCounts.get(job.domain) || 0) + 1);
  }
  const topDomains = Array.from(domainCounts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  // Chart data
  const bandwidthChartData = [
    { name: 'Used', value: monthlyCount },
    { name: 'Remaining', value: Math.max(MONTHLY_LIMIT - monthlyCount, 0) },
  ];

  const bandwidthColor = isOverLimit ? '#ef4444' : monthlyCount >= 30 ? '#f59e0b' : '#282727';

  const salespersonChartData = salespersonBreakdown.map((sp) => ({
    name: sp.name.length > 14 ? sp.name.substring(0, 14) + '...' : sp.name,
    fullName: sp.name,
    email: sp.email,
    jobs: sp.count,
  }));

  const industryChartData = industryBreakdown.slice(0, 8).map((entry) => ({
    name: entry.industry,
    fullName: entry.industry,
    value: entry.count,
  }));

  if (!seller) {
    return (
      <div className="p-6 lg:p-8">
        <div className="card p-12 text-center max-w-md mx-auto">
          <div className="w-16 h-16 mx-auto mb-4 rounded-xl bg-slate-100 flex items-center justify-center">
            <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-slate-900 mb-2">Seller Not Found</h2>
          <p className="text-base text-slate-500 mb-5">This seller may have been deleted.</p>
          <Link href="/dashboard/sellers" className="btn-primary">
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Sellers
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => router.back()}
          className="text-slate-500 hover:text-slate-900 mb-3 inline-flex items-center text-sm font-medium transition-colors"
        >
          <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Sellers
        </button>

        <div className="flex items-center space-x-3.5">
          <div className="w-14 h-14 rounded-xl bg-[#282727] flex items-center justify-center shadow-lg">
            <span className="text-white font-bold text-2xl">{seller.name.charAt(0)}</span>
          </div>
          <div>
            <h1 className="text-2xl lg:text-3xl font-bold text-slate-900 tracking-tight">{seller.name}</h1>
            <p className="text-base text-slate-500">Created {formatDate(seller.created_at)}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Analytics Column */}
        <div className="lg:col-span-1 space-y-6">
          {/* Monthly Bandwidth - Donut Chart */}
          <div className="card p-6">
            <h2 className="text-base font-semibold text-slate-900 mb-4">Monthly Bandwidth</h2>
            <div className="relative flex items-center justify-center" style={{ height: 200 }}>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={bandwidthChartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={62}
                    outerRadius={85}
                    paddingAngle={2}
                    dataKey="value"
                    startAngle={90}
                    endAngle={-270}
                    stroke="none"
                  >
                    <Cell fill={bandwidthColor} />
                    <Cell fill="#e2e8f0" />
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              {/* Center text overlay */}
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className={`text-4xl font-bold ${isOverLimit ? 'text-red-600' : monthlyCount >= 30 ? 'text-amber-600' : 'text-slate-900'}`}>
                  {monthlyCount}
                </span>
                <span className="text-sm text-slate-400">of {MONTHLY_LIMIT}</span>
              </div>
            </div>
            <p className={`text-sm text-center mt-2 ${isOverLimit ? 'text-red-600 font-medium' : 'text-slate-400'}`}>
              {isOverLimit
                ? 'Monthly limit reached'
                : `${MONTHLY_LIMIT - monthlyCount} remaining this month`}
            </p>
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-2 gap-4">
            <div className="card p-4">
              <p className="text-sm text-slate-400 mb-0.5">Total</p>
              <p className="text-2xl font-bold text-slate-900">{jobs.length}</p>
            </div>
            <div className="card p-4">
              <p className="text-sm text-slate-400 mb-0.5">Completed</p>
              <p className="text-2xl font-bold text-emerald-600">{completedCount}</p>
            </div>
            <div className="card p-4">
              <p className="text-sm text-slate-400 mb-0.5">Processing</p>
              <p className="text-2xl font-bold text-blue-600">{processingCount}</p>
            </div>
            <div className="card p-4">
              <p className="text-sm text-slate-400 mb-0.5">Failed</p>
              <p className="text-2xl font-bold text-red-600">{failedCount}</p>
            </div>
          </div>

          {/* Salesperson Activity - Bar Chart */}
          <div className="card p-6">
            <h2 className="text-base font-semibold text-slate-900 mb-4">Salesperson Activity</h2>
            {salespersonBreakdown.length === 0 ? (
              <p className="text-sm text-slate-400">No salesperson data yet.</p>
            ) : (
              <div>
                <ResponsiveContainer width="100%" height={Math.max(salespersonChartData.length * 48 + 24, 150)}>
                  <BarChart
                    data={salespersonChartData}
                    layout="vertical"
                    margin={{ top: 0, right: 24, left: 0, bottom: 0 }}
                  >
                    <XAxis type="number" hide />
                    <YAxis
                      type="category"
                      dataKey="name"
                      width={100}
                      tick={{ fontSize: 12, fill: '#64748b' }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(148, 163, 184, 0.1)' }} />
                    <Bar
                      dataKey="jobs"
                      radius={[0, 4, 4, 0]}
                      barSize={20}
                    >
                      {salespersonChartData.map((_, i) => (
                        <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                {/* Legend with email */}
                <div className="mt-3 space-y-2 border-t border-slate-100 pt-3">
                  {salespersonBreakdown.map((sp, i) => (
                    <div key={sp.email} className="flex items-center justify-between text-sm">
                      <div className="flex items-center space-x-2 min-w-0">
                        <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: CHART_COLORS[i % CHART_COLORS.length] }} />
                        <span className="text-slate-600 truncate">{sp.email}</span>
                      </div>
                      <span className="text-slate-500 font-medium ml-2 flex-shrink-0">{sp.count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Industry Trends - Pie Chart */}
          <div className="card p-6">
            <h2 className="text-base font-semibold text-slate-900 mb-4">Industry Trends</h2>
            {industryBreakdown.length === 0 ? (
              <p className="text-sm text-slate-400">Industry data appears after jobs complete.</p>
            ) : (
              <div>
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie
                      data={industryChartData}
                      cx="50%"
                      cy="50%"
                      outerRadius={90}
                      innerRadius={45}
                      dataKey="value"
                      paddingAngle={1}
                      stroke="none"
                    >
                      {industryChartData.map((_, i) => (
                        <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip content={<ChartTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
                {/* Legend */}
                <div className="mt-3 space-y-2 border-t border-slate-100 pt-3">
                  {industryBreakdown.slice(0, 8).map((entry, i) => (
                    <div key={entry.industry} className="flex items-center justify-between text-sm">
                      <div className="flex items-center space-x-2 min-w-0">
                        <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: CHART_COLORS[i % CHART_COLORS.length] }} />
                        <span className="text-slate-600 truncate">{entry.industry}</span>
                      </div>
                      <span className="text-slate-500 font-medium ml-2 flex-shrink-0">{entry.count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Top Domains */}
          {topDomains.length > 1 && (
            <div className="card p-6">
              <h2 className="text-base font-semibold text-slate-900 mb-4">Top Domains</h2>
              <div className="space-y-2.5">
                {topDomains.map(([domain, count], i) => (
                  <div key={domain} className="flex items-center justify-between">
                    <div className="flex items-center space-x-2 min-w-0">
                      <span className="text-sm text-slate-400 w-5 text-right flex-shrink-0">{i + 1}.</span>
                      <p className="text-base text-slate-700 truncate">{domain}</p>
                    </div>
                    <span className="text-sm font-medium text-slate-500 bg-slate-100 px-2.5 py-0.5 rounded-md ml-2 flex-shrink-0">
                      {count}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Jobs List Column — grouped by month, stretches to match left */}
        <div className="lg:col-span-2 flex">
          <div className="card p-6 h-full flex flex-col w-full">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-base font-semibold text-slate-900">Assigned Jobs</h2>
              <Link href="/dashboard" className="text-sm font-medium text-blue-600 hover:text-blue-700">
                + New Job
              </Link>
            </div>

            {jobs.length === 0 ? (
              <div className="text-center py-12 flex-1 flex flex-col items-center justify-center">
                <div className="w-16 h-16 mx-auto mb-4 rounded-xl bg-slate-100 flex items-center justify-center">
                  <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <h3 className="text-base font-semibold text-slate-900 mb-1">No jobs assigned</h3>
                <p className="text-sm text-slate-500">Assign jobs to this seller from the New Profile form.</p>
              </div>
            ) : (
              <div className="space-y-7 flex-1 overflow-y-auto">
                {Object.entries(monthGrouped).map(([monthKey, monthJobs]) => {
                  const monthCompleted = monthJobs.filter((j: any) => j.status === 'completed').length;
                  const monthTotal = monthJobs.length;
                  return (
                    <div key={monthKey}>
                      {/* Month header */}
                      <div className="flex items-center justify-between mb-3">
                        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider">
                          {formatMonthLabel(monthKey)}
                        </h3>
                        <div className="flex items-center gap-3">
                          <span className="text-sm text-slate-400">
                            {monthTotal} {monthTotal === 1 ? 'job' : 'jobs'}
                          </span>
                          <span className="text-sm text-emerald-600 font-medium">
                            {monthCompleted} completed
                          </span>
                        </div>
                      </div>

                      {/* Jobs in this month */}
                      <div className="space-y-2.5">
                        {(monthJobs as any[]).map((job) => {
                          const status = statusConfig[job.status] || statusConfig.pending;
                          const isClickable = job.status === 'completed';
                          const isDeleting = deleteConfirmJobId === job.job_id;

                          const jobRow = (
                            <div
                              className={`relative group flex items-center justify-between p-4 rounded-lg bg-slate-50/80 hover:bg-slate-100 transition-colors ${
                                isClickable ? 'cursor-pointer' : ''
                              }`}
                            >
                              {/* Delete confirmation overlay */}
                              {isDeleting && (
                                <div className="absolute inset-0 bg-white/95 backdrop-blur-sm rounded-lg z-10 flex items-center justify-center gap-3">
                                  <span className="text-sm font-medium text-slate-900">Delete this job?</span>
                                  <button
                                    onClick={(e) => { e.preventDefault(); e.stopPropagation(); setDeleteConfirmJobId(null); }}
                                    className="px-3 py-1.5 text-sm font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-md"
                                  >
                                    Cancel
                                  </button>
                                  <button
                                    onClick={(e) => { e.preventDefault(); e.stopPropagation(); removeJob(job.job_id); setDeleteConfirmJobId(null); }}
                                    className="px-3 py-1.5 text-sm font-medium text-white bg-red-500 hover:bg-red-600 rounded-md"
                                  >
                                    Delete
                                  </button>
                                </div>
                              )}

                              <div className="flex items-center space-x-3 min-w-0">
                                <div className="w-9 h-9 rounded-md bg-white shadow-sm flex items-center justify-center flex-shrink-0">
                                  <span className="text-slate-700 font-semibold text-sm">
                                    {job.company_name.charAt(0)}
                                  </span>
                                </div>
                                <div className="min-w-0">
                                  <p className={`text-base font-medium text-slate-900 truncate ${isClickable ? 'group-hover:text-blue-600' : ''}`}>{job.company_name}</p>
                                  <p className="text-sm text-slate-400 truncate">
                                    {job.domain}
                                    {job.requested_by && (
                                      <span> &middot; {job.requested_by}</span>
                                    )}
                                  </p>
                                </div>
                              </div>
                              <div className="flex items-center space-x-3 flex-shrink-0 ml-3">
                                <span
                                  className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ring-1 ring-inset ${status.bg} ${status.text} ${status.ring}`}
                                >
                                  {(job.status === 'processing' || job.status === 'pending') && (
                                    <span className={`w-1.5 h-1.5 rounded-full ${status.dot} mr-1 animate-pulse`} />
                                  )}
                                  {status.label}
                                </span>
                                <span className="text-sm text-slate-400">{formatTimeAgo(job.created_at)}</span>
                                {/* Delete button */}
                                <button
                                  onClick={(e) => { e.preventDefault(); e.stopPropagation(); setDeleteConfirmJobId(job.job_id); }}
                                  className="p-1.5 rounded-md text-slate-400 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all"
                                  title="Delete job"
                                >
                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                  </svg>
                                </button>
                                {isClickable && (
                                  <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                  </svg>
                                )}
                              </div>
                            </div>
                          );

                          if (isClickable && !isDeleting) {
                            return (
                              <Link key={job.job_id} href={`/dashboard/jobs/${job.job_id}`}>
                                {jobRow}
                              </Link>
                            );
                          }

                          return <div key={job.job_id}>{jobRow}</div>;
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
