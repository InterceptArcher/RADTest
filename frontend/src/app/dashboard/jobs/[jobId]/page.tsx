'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useJobs } from '@/hooks/useJobs';
import {
  ExecutiveSnapshotCard,
  BuyingSignalsCard,
  StakeholderMapCard,
  SalesProgramCard,
  OutreachGeneratorModal,
  NewsIntelligenceCard,
} from '@/components/intelligence';
import type { StakeholderRoleType } from '@/types';

interface InfoItemProps {
  label: string;
  value: string | number | undefined | null;
  icon?: React.ReactNode;
}

function InfoItem({ label, value, icon }: InfoItemProps) {
  if (!value) return null;
  return (
    <div className="flex items-start space-x-3 py-3 border-b border-slate-100 last:border-0">
      {icon && <div className="text-slate-400 mt-0.5">{icon}</div>}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-slate-500">{label}</p>
        <p className="text-slate-900 font-medium truncate">{value}</p>
      </div>
    </div>
  );
}

interface BadgeListProps {
  items: string[] | string | undefined;
  variant?: 'default' | 'primary' | 'success' | 'purple';
}

function BadgeList({ items, variant = 'default' }: BadgeListProps) {
  if (!items) return <span className="text-slate-400 text-sm">Not available</span>;

  const itemArray = Array.isArray(items)
    ? items
    : items.split(',').map((s) => s.trim()).filter(Boolean);

  if (itemArray.length === 0) {
    return <span className="text-slate-400 text-sm">Not available</span>;
  }

  const variantClasses = {
    default: 'bg-slate-100 text-slate-700 ring-slate-500/20',
    primary: 'bg-primary-50 text-primary-700 ring-primary-600/20',
    success: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20',
    purple: 'bg-purple-50 text-purple-700 ring-purple-600/20',
  };

  return (
    <div className="flex flex-wrap gap-2">
      {itemArray.map((item, index) => (
        <span
          key={index}
          className={`inline-flex items-center px-3 py-1.5 rounded-lg text-sm font-medium ring-1 ring-inset ${variantClasses[variant]}`}
        >
          {item}
        </span>
      ))}
    </div>
  );
}

export default function JobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { getJob } = useJobs();

  // Outreach modal state
  const [outreachModalOpen, setOutreachModalOpen] = useState(false);
  const [selectedRoleType, setSelectedRoleType] = useState<StakeholderRoleType>('CIO');
  const [selectedStakeholderName, setSelectedStakeholderName] = useState<string | undefined>();

  const jobId = params.jobId as string;
  const job = getJob(jobId);

  const handleGenerateOutreach = (roleType: StakeholderRoleType, stakeholderName?: string) => {
    setSelectedRoleType(roleType);
    setSelectedStakeholderName(stakeholderName);
    setOutreachModalOpen(true);
  };

  if (!job) {
    return (
      <div className="p-8 lg:p-10">
        <div className="card p-12 text-center max-w-md mx-auto">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-slate-100 flex items-center justify-center">
            <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-slate-900 mb-2">
            Job Not Found
          </h2>
          <p className="text-slate-600 mb-6">
            This job may have expired or does not exist.
          </p>
          <Link href="/dashboard/jobs" className="btn-primary">
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Jobs
          </Link>
        </div>
      </div>
    );
  }

  if (job.status !== 'completed' || !job.result?.validated_data) {
    return (
      <div className="p-8 lg:p-10">
        <div className="card p-12 text-center max-w-md mx-auto">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-primary-50 flex items-center justify-center">
            <svg className="w-8 h-8 text-primary-500 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-slate-900 mb-2">
            Processing...
          </h2>
          <p className="text-slate-600 mb-6">
            This job is still being processed. Please wait for it to complete.
          </p>
          <Link href="/dashboard/jobs" className="btn-secondary">
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Jobs
          </Link>
        </div>
      </div>
    );
  }

  // Use job.result directly for top-level fields, fallback to validated_data
  const data = {
    ...job.result.validated_data,
    // Override with top-level fields if they exist
    company_name: job.result.company_name || job.result.validated_data?.company_name,
    domain: job.result.domain || job.result.validated_data?.domain,
    industry: job.result.industry || job.result.validated_data?.industry,
    sub_industry: job.result.sub_industry || job.result.validated_data?.sub_industry,
    employee_count: job.result.employee_count || job.result.validated_data?.employee_count,
    annual_revenue: job.result.annual_revenue || job.result.validated_data?.annual_revenue,
    headquarters: job.result.headquarters || job.result.validated_data?.headquarters,
    geographic_reach: job.result.geographic_reach || job.result.validated_data?.geographic_reach,
    founded_year: job.result.founded_year || job.result.validated_data?.founded_year,
    founders: job.result.founders || job.result.validated_data?.founders,
    ceo: job.result.ceo || job.result.validated_data?.ceo,
    target_market: job.result.target_market || job.result.validated_data?.target_market,
    customer_segments: job.result.customer_segments || job.result.validated_data?.customer_segments,
    products: job.result.products || job.result.validated_data?.products,
    technologies: job.result.technologies || job.result.validated_data?.technologies,
    competitors: job.result.competitors || job.result.validated_data?.competitors,
    company_type: job.result.company_type || job.result.validated_data?.company_type,
    linkedin_url: job.result.linkedin_url || job.result.validated_data?.linkedin_url,
  };

  // Extract new intelligence sections from result
  const executiveSnapshot = job.result.executive_snapshot;
  const buyingSignals = job.result.buying_signals;
  const stakeholderMap = job.result.stakeholder_map;
  const salesProgram = job.result.sales_program;
  const newsIntelligence = job.result.news_intelligence;

  return (
    <div className="p-8 lg:p-10">
      {/* Header */}
      <div className="mb-8">
        <button
          onClick={() => router.back()}
          className="text-slate-500 hover:text-slate-900 mb-4 inline-flex items-center text-sm font-medium transition-colors"
        >
          <svg
            className="w-5 h-5 mr-1"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
          Back to Jobs
        </button>

        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6">
          <div>
            <div className="flex items-center space-x-3 mb-2">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center shadow-lg shadow-primary-500/25">
                <span className="text-white font-bold text-lg">
                  {(data.company_name || job.companyName).charAt(0)}
                </span>
              </div>
              <div>
                <h1 className="text-2xl lg:text-3xl font-bold text-slate-900 tracking-tight">
                  {data.company_name || job.companyName}
                </h1>
                <p className="text-slate-500">{job.domain}</p>
              </div>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="card px-4 py-3">
              <p className="text-xs text-slate-500 mb-0.5">Confidence Score</p>
              <p className="text-2xl font-bold text-emerald-600">
                {Math.round(job.result.confidence_score * 100)}%
              </p>
            </div>
            <Link
              href={`/dashboard/jobs/${jobId}/debug`}
              className="btn-secondary"
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
              Debug Mode
            </Link>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Info */}
        <div className="lg:col-span-2 space-y-6">
          {/* Overview */}
          <div className="card p-6">
            <div className="flex items-center space-x-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center">
                <svg className="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
              </div>
              <h2 className="text-lg font-semibold text-slate-900">Company Overview</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8">
              <InfoItem label="Industry" value={data.industry} />
              <InfoItem label="Sub-Industry" value={(data as any).sub_industry} />
              <InfoItem label="Employee Count" value={data.employee_count} />
              <InfoItem label="Annual Revenue" value={(data as any).annual_revenue || data.revenue} />
              <InfoItem label="Headquarters" value={data.headquarters} />
              <InfoItem label="Founded" value={data.founded_year} />
              <InfoItem label="CEO" value={data.ceo} />
              <InfoItem label="Company Type" value={(data as any).company_type} />
            </div>
          </div>

          {/* Executive Snapshot - New Intelligence Section */}
          {executiveSnapshot && (
            <ExecutiveSnapshotCard
              snapshot={executiveSnapshot}
              companyName={data.company_name || job.companyName}
              industry={data.industry}
            />
          )}

          {/* Buying Signals - New Intelligence Section */}
          {buyingSignals && (
            <BuyingSignalsCard signals={buyingSignals} />
          )}

          {/* News Intelligence - New Intelligence Section */}
          {newsIntelligence && (
            <NewsIntelligenceCard
              newsIntelligence={newsIntelligence}
              companyName={data.company_name || job.companyName}
            />
          )}

          {/* Stakeholder Map - New Intelligence Section */}
          {stakeholderMap && (
            <StakeholderMapCard
              stakeholderMap={stakeholderMap}
              onGenerateOutreach={handleGenerateOutreach}
            />
          )}

          {/* Sales Program - New Intelligence Section */}
          {salesProgram && (
            <SalesProgramCard
              program={salesProgram}
              onGenerateOutreach={(roleType) => handleGenerateOutreach(roleType)}
            />
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Quick Actions */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Quick Actions</h2>
            <div className="space-y-3">
              {/* View Slideshow Button */}
              {job.result.slideshow_url && (
                <a
                  href={job.result.slideshow_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-primary w-full"
                >
                  <svg
                    className="w-5 h-5 mr-2"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z"
                    />
                  </svg>
                  View Slideshow
                </a>
              )}
              <Link
                href={`/dashboard/jobs/${jobId}/debug`}
                className="btn-secondary w-full"
              >
                <svg
                  className="w-5 h-5 mr-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"
                  />
                </svg>
                View Debug Info
              </Link>
            </div>
          </div>

          {/* Contact Info */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Contact & Links</h2>
            <div className="space-y-3">
              <a
                href={`https://${job.domain}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center text-primary-600 hover:text-primary-700 font-medium transition-colors"
              >
                <svg
                  className="w-5 h-5 mr-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"
                  />
                </svg>
                {job.domain}
              </a>
              {(data as any).linkedin_url && (
                <a
                  href={(data as any).linkedin_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center text-primary-600 hover:text-primary-700 font-medium transition-colors"
                >
                  <svg
                    className="w-5 h-5 mr-2"
                    fill="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z" />
                  </svg>
                  LinkedIn
                </a>
              )}
            </div>
          </div>

          {/* Customer Segments */}
          {(data as any).customer_segments && (
            <div className="card p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">Customer Segments</h2>
              <BadgeList items={(data as any).customer_segments} />
            </div>
          )}

          {/* Founders */}
          {(data as any).founders && (data as any).founders.length > 0 && (
            <div className="card p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">Founders</h2>
              <ul className="space-y-3">
                {(data as any).founders.map((founder: string, index: number) => (
                  <li key={index} className="flex items-center">
                    <div className="w-9 h-9 bg-gradient-to-br from-slate-200 to-slate-100 rounded-full flex items-center justify-center mr-3">
                      <span className="text-slate-600 font-semibold text-sm">
                        {founder.charAt(0)}
                      </span>
                    </div>
                    <span className="text-slate-900 font-medium">{founder}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Geographic Reach */}
          {((data as any).geographic_reach || data.geographic_reach) && (
            <div className="card p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">Geographic Reach</h2>
              <BadgeList items={(data as any).geographic_reach || data.geographic_reach} variant="primary" />
            </div>
          )}

          {/* Products & Services */}
          {(data as any).products && (
            <div className="card p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">Products & Services</h2>
              <BadgeList items={(data as any).products} variant="purple" />
            </div>
          )}

          {/* Technologies */}
          {((data as any).technologies || data.technology) && (
            <div className="card p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">Technologies</h2>
              <BadgeList items={(data as any).technologies || data.technology} variant="success" />
            </div>
          )}

          {/* Competitors */}
          {(data as any).competitors && (
            <div className="card p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">Competitors</h2>
              <BadgeList items={(data as any).competitors} />
            </div>
          )}
        </div>
      </div>

      {/* Outreach Generator Modal */}
      <OutreachGeneratorModal
        isOpen={outreachModalOpen}
        onClose={() => setOutreachModalOpen(false)}
        jobId={jobId}
        roleType={selectedRoleType}
        stakeholderName={selectedStakeholderName}
      />
    </div>
  );
}
