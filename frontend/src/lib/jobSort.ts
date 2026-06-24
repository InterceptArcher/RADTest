/**
 * Job list ordering. Pure + deterministic so it can be unit-tested without
 * rendering. The Jobs page defaults to 'recent' (newest first); 'seller' is an
 * opt-in alphabetical-by-seller view.
 */
import type { JobWithMetadata } from '@/types';

export type SortMode = 'recent' | 'seller';

const ts = (j: JobWithMetadata) =>
  new Date(j.completedAt || j.createdAt).getTime();

/** Newest first by completedAt (falling back to createdAt). */
function byRecency(a: JobWithMetadata, b: JobWithMetadata): number {
  return ts(b) - ts(a);
}

/**
 * Return a NEW array sorted by the given mode (never mutates the input).
 * - 'recent': newest first.
 * - 'seller': seller name A–Z (case-insensitive); jobs with no seller sort
 *   last; ties broken by recency (newest first).
 */
export function sortJobs(jobs: JobWithMetadata[], mode: SortMode): JobWithMetadata[] {
  const copy = [...jobs];
  if (mode === 'recent') {
    return copy.sort(byRecency);
  }
  return copy.sort((a, b) => {
    const an = (a.sellerName || '').trim();
    const bn = (b.sellerName || '').trim();
    // Unsellered jobs always sink to the bottom.
    if (!an && bn) return 1;
    if (an && !bn) return -1;
    const cmp = an.toLowerCase().localeCompare(bn.toLowerCase());
    return cmp !== 0 ? cmp : byRecency(a, b);
  });
}
