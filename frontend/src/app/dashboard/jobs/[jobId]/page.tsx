'use client';

import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useJobs } from '@/hooks/useJobs';

interface InfoItemProps {
  label: string;
  value: string | number | undefined | null;
  icon?: React.ReactNode;
}

function InfoItem({ label, value, icon }: InfoItemProps) {
  if (!value) return null;
  return (
    <div className="flex items-start space-x-3 py-3">
      {icon && <div className="text-gray-400 mt-0.5">{icon}</div>}
      <div>
        <p className="text-sm text-gray-500">{label}</p>
        <p className="text-gray-900 font-medium">{value}</p>
      </div>
    </div>
  );
}

interface BadgeListProps {
  items: string[] | string | undefined;
  color?: string;
}

function BadgeList({ items, color = 'gray' }: BadgeListProps) {
  if (!items) return <span className="text-gray-400">Not available</span>;

  const itemArray = Array.isArray(items)
    ? items
    : items.split(',').map((s) => s.trim()).filter(Boolean);

  if (itemArray.length === 0) {
    return <span className="text-gray-400">Not available</span>;
  }

  const colorClasses = {
    gray: 'bg-gray-100 text-gray-800',
    blue: 'bg-blue-100 text-blue-800',
    green: 'bg-green-100 text-green-800',
    purple: 'bg-purple-100 text-purple-800',
  };

  return (
    <div className="flex flex-wrap gap-2">
      {itemArray.map((item, index) => (
        <span
          key={index}
          className={`px-3 py-1 rounded-full text-sm ${colorClasses[color as keyof typeof colorClasses] || colorClasses.gray}`}
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

  const jobId = params.jobId as string;
  const job = getJob(jobId);

  if (!job) {
    return (
      <div className="p-8">
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Job Not Found
          </h2>
          <p className="text-gray-600 mb-4">
            This job may have expired or does not exist.
          </p>
          <Link
            href="/dashboard/jobs"
            className="text-blue-600 hover:text-blue-800 font-medium"
          >
            ← Back to Jobs
          </Link>
        </div>
      </div>
    );
  }

  if (job.status !== 'completed' || !job.result?.validated_data) {
    return (
      <div className="p-8">
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Job Not Complete
          </h2>
          <p className="text-gray-600 mb-4">
            This job is still processing. Please wait for it to complete.
          </p>
          <Link
            href="/dashboard/jobs"
            className="text-blue-600 hover:text-blue-800 font-medium"
          >
            ← Back to Jobs
          </Link>
        </div>
      </div>
    );
  }

  const data = job.result.validated_data;

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <button
          onClick={() => router.back()}
          className="text-gray-600 hover:text-gray-900 mb-4 inline-flex items-center"
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

        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              {data.company_name || job.companyName}
            </h1>
            <p className="mt-1 text-lg text-gray-600">{job.domain}</p>
          </div>
          <div className="flex items-center space-x-3">
            <div className="text-right">
              <p className="text-sm text-gray-500">Confidence Score</p>
              <p className="text-2xl font-bold text-green-600">
                {Math.round(job.result.confidence_score * 100)}%
              </p>
            </div>
            <Link
              href={`/dashboard/jobs/${jobId}/debug`}
              className="px-4 py-2 bg-gray-100 text-gray-700 font-medium rounded-lg hover:bg-gray-200 transition-colors"
            >
              Debug Mode
            </Link>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Info */}
        <div className="lg:col-span-2 space-y-6">
          {/* Overview */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Company Overview
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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

          {/* Geographic Reach */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Geographic Reach
            </h2>
            <BadgeList items={(data as any).geographic_reach || data.geographic_reach} color="blue" />
          </div>

          {/* Products */}
          {(data as any).products && (
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Products & Services
              </h2>
              <BadgeList items={(data as any).products} color="purple" />
            </div>
          )}

          {/* Technologies */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Technologies
            </h2>
            <BadgeList items={(data as any).technologies || data.technology} color="green" />
          </div>

          {/* Competitors */}
          {(data as any).competitors && (
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Competitors
              </h2>
              <BadgeList items={(data as any).competitors} />
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Quick Actions */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Quick Actions
            </h2>
            <div className="space-y-3">
              {job.result.slideshow_url && (
                <a
                  href={job.result.slideshow_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full flex items-center justify-center px-4 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
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
                className="w-full flex items-center justify-center px-4 py-3 bg-gray-100 text-gray-700 font-medium rounded-lg hover:bg-gray-200 transition-colors"
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
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Contact & Links
            </h2>
            <div className="space-y-3">
              <a
                href={`https://${job.domain}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center text-blue-600 hover:text-blue-800"
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
                  className="flex items-center text-blue-600 hover:text-blue-800"
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
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Customer Segments
              </h2>
              <BadgeList items={(data as any).customer_segments} />
            </div>
          )}

          {/* Founders */}
          {(data as any).founders && (data as any).founders.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Founders
              </h2>
              <ul className="space-y-2">
                {(data as any).founders.map((founder: string, index: number) => (
                  <li key={index} className="flex items-center">
                    <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center mr-3">
                      <span className="text-gray-600 font-medium text-sm">
                        {founder.charAt(0)}
                      </span>
                    </div>
                    <span className="text-gray-900">{founder}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
