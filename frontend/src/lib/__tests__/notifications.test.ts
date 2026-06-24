import { toNotifications, unseenCount } from '@/lib/notifications';
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
    ...partial,
  } as JobWithMetadata;
}

describe('toNotifications', () => {
  const running = job({ jobId: 'r', status: 'processing' });
  const pending = job({ jobId: 'p', status: 'pending' });
  const done = job({ jobId: 'd', status: 'completed', completedAt: '2026-06-20T10:00:00.000Z' });
  const failed = job({ jobId: 'f', status: 'failed', createdAt: '2026-06-22T10:00:00.000Z' });

  it('includes only completed and failed jobs', () => {
    const out = toNotifications([running, pending, done, failed]);
    expect(out.map((n) => n.jobId).sort()).toEqual(['d', 'f']);
  });

  it('sorts newest first by completedAt/createdAt', () => {
    const out = toNotifications([done, failed]);
    expect(out.map((n) => n.jobId)).toEqual(['f', 'd']);
  });

  it('tags kind from job status', () => {
    const out = toNotifications([done, failed]);
    expect(out.find((n) => n.jobId === 'd')!.kind).toBe('completed');
    expect(out.find((n) => n.jobId === 'f')!.kind).toBe('failed');
  });
});

describe('unseenCount', () => {
  const a = job({ jobId: 'a', status: 'completed' });
  const b = job({ jobId: 'b', status: 'failed' });
  const c = job({ jobId: 'c', status: 'processing' });

  it('counts finished jobs not in the seen set', () => {
    expect(unseenCount([a, b, c], [])).toBe(2);
    expect(unseenCount([a, b, c], ['a'])).toBe(1);
    expect(unseenCount([a, b, c], ['a', 'b'])).toBe(0);
  });

  it('accepts a Set as well as an array', () => {
    expect(unseenCount([a, b, c], new Set(['b']))).toBe(1);
  });

  it('ignores seen ids that are not finished jobs', () => {
    expect(unseenCount([a, b, c], ['c'])).toBe(2);
  });
});
