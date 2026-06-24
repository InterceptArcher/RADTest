import { sortJobs } from '@/lib/jobSort';
import type { JobWithMetadata } from '@/types';

function job(partial: Partial<JobWithMetadata>): JobWithMetadata {
  return {
    jobId: partial.jobId || 'j',
    companyName: partial.companyName || 'Co',
    domain: partial.domain || 'co.com',
    status: partial.status || 'completed',
    progress: partial.progress ?? 100,
    currentStep: partial.currentStep || 'Done',
    createdAt: partial.createdAt || '2026-01-01T00:00:00.000Z',
    completedAt: partial.completedAt,
    sellerName: partial.sellerName,
    ...partial,
  } as JobWithMetadata;
}

describe('sortJobs', () => {
  const older = job({ jobId: 'a', sellerName: 'Zoe', createdAt: '2026-06-01T10:00:00.000Z' });
  const newer = job({ jobId: 'b', sellerName: 'Adam', createdAt: '2026-06-20T10:00:00.000Z' });
  const newest = job({ jobId: 'c', sellerName: 'Mary', createdAt: '2026-06-24T10:00:00.000Z' });

  it('does not mutate the input array', () => {
    const input = [older, newer, newest];
    const copy = [...input];
    sortJobs(input, 'recent');
    expect(input).toEqual(copy);
  });

  it('recent: newest createdAt first', () => {
    const out = sortJobs([older, newest, newer], 'recent');
    expect(out.map((j) => j.jobId)).toEqual(['c', 'b', 'a']);
  });

  it('seller: alphabetical by seller name (case-insensitive)', () => {
    const out = sortJobs([older, newer, newest], 'seller');
    expect(out.map((j) => j.sellerName)).toEqual(['Adam', 'Mary', 'Zoe']);
  });

  it('seller: jobs without a seller sort last', () => {
    const noSeller = job({ jobId: 'n', sellerName: undefined, createdAt: '2026-06-30T00:00:00.000Z' });
    const out = sortJobs([noSeller, newer], 'seller');
    expect(out[out.length - 1].jobId).toBe('n');
  });

  it('seller: ties broken by recency (newest first)', () => {
    const s1 = job({ jobId: 's1', sellerName: 'Sam', createdAt: '2026-06-01T00:00:00.000Z' });
    const s2 = job({ jobId: 's2', sellerName: 'Sam', createdAt: '2026-06-10T00:00:00.000Z' });
    const out = sortJobs([s1, s2], 'seller');
    expect(out.map((j) => j.jobId)).toEqual(['s2', 's1']);
  });
});
