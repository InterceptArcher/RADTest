import type { SellerJob } from '@/types';

/**
 * Group jobs by year-month (e.g. "2026-03"), sorted descending.
 */
export function groupJobsByMonth(
  jobs: Pick<SellerJob, 'job_id' | 'created_at'>[]
): Record<string, typeof jobs> {
  const groups: Record<string, typeof jobs> = {};

  for (const job of jobs) {
    const d = new Date(job.created_at);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    if (!groups[key]) groups[key] = [];
    groups[key].push(job);
  }

  // Sort keys descending
  const sorted: Record<string, typeof jobs> = {};
  for (const key of Object.keys(groups).sort().reverse()) {
    sorted[key] = groups[key];
  }
  return sorted;
}

interface SalespersonEntry {
  email: string;
  name: string;
  count: number;
}

/**
 * Break down jobs by salesperson (requested_by email), returning name + count.
 */
export function getSalespersonBreakdown(
  jobs: Pick<SellerJob, 'requested_by' | 'salesperson_name'>[]
): SalespersonEntry[] {
  if (jobs.length === 0) return [];

  const map = new Map<string, { name: string; count: number }>();

  for (const job of jobs) {
    const email = job.requested_by || 'Unknown';
    const existing = map.get(email);
    if (existing) {
      existing.count++;
      // Prefer a non-empty salesperson_name
      if (job.salesperson_name && !existing.name) {
        existing.name = job.salesperson_name;
      }
    } else {
      map.set(email, {
        name: job.salesperson_name || email.split('@')[0],
        count: 1,
      });
    }
  }

  return Array.from(map.entries())
    .map(([email, data]) => ({ email, name: data.name, count: data.count }))
    .sort((a, b) => b.count - a.count);
}

interface IndustryEntry {
  industry: string;
  count: number;
}

/**
 * Count industries from result_data across jobs.
 * Checks top-level industry, then validated_data.industry as fallback.
 */
export function getIndustryBreakdown(
  jobs: { result_data?: { industry?: string; validated_data?: { industry?: string } } | null }[]
): IndustryEntry[] {
  if (jobs.length === 0) return [];

  const map = new Map<string, number>();

  for (const job of jobs) {
    const industry = job.result_data?.industry || job.result_data?.validated_data?.industry;
    if (industry) {
      map.set(industry, (map.get(industry) || 0) + 1);
    }
  }

  return Array.from(map.entries())
    .map(([industry, count]) => ({ industry, count }))
    .sort((a, b) => b.count - a.count);
}
