/**
 * Tests for Seller Detail Page — metrics and month-grouped jobs.
 * TDD: These tests verify salesperson breakdown, industry trends,
 * and month-grouped job display before implementation.
 */

// Helper functions extracted for testability
import { groupJobsByMonth, getSalespersonBreakdown, getIndustryBreakdown } from '../helpers';

describe('groupJobsByMonth', () => {
  const jobs = [
    { job_id: '1', company_name: 'A', domain: 'a.com', status: 'completed' as const, created_at: '2026-03-10T10:00:00Z', seller_id: 's1', requested_by: 'alice@test.com' },
    { job_id: '2', company_name: 'B', domain: 'b.com', status: 'processing' as const, created_at: '2026-03-05T10:00:00Z', seller_id: 's1', requested_by: 'bob@test.com' },
    { job_id: '3', company_name: 'C', domain: 'c.com', status: 'completed' as const, created_at: '2026-02-20T10:00:00Z', seller_id: 's1', requested_by: 'alice@test.com' },
    { job_id: '4', company_name: 'D', domain: 'd.com', status: 'failed' as const, created_at: '2026-01-15T10:00:00Z', seller_id: 's1', requested_by: 'bob@test.com' },
  ];

  it('groups jobs by year-month descending', () => {
    const grouped = groupJobsByMonth(jobs);
    const keys = Object.keys(grouped);
    expect(keys).toEqual(['2026-03', '2026-02', '2026-01']);
  });

  it('places correct jobs in each month', () => {
    const grouped = groupJobsByMonth(jobs);
    expect(grouped['2026-03']).toHaveLength(2);
    expect(grouped['2026-02']).toHaveLength(1);
    expect(grouped['2026-01']).toHaveLength(1);
  });

  it('returns empty object for empty input', () => {
    expect(groupJobsByMonth([])).toEqual({});
  });
});

describe('getSalespersonBreakdown', () => {
  const jobs = [
    { job_id: '1', requested_by: 'alice@test.com', salesperson_name: 'Alice Smith', status: 'completed' as const },
    { job_id: '2', requested_by: 'alice@test.com', salesperson_name: 'Alice Smith', status: 'processing' as const },
    { job_id: '3', requested_by: 'bob@test.com', salesperson_name: 'Bob Jones', status: 'completed' as const },
    { job_id: '4', requested_by: 'bob@test.com', status: 'failed' as const },
  ];

  it('returns counts per salesperson sorted by count descending', () => {
    const breakdown = getSalespersonBreakdown(jobs as any);
    expect(breakdown[0].email).toBe('alice@test.com');
    expect(breakdown[0].count).toBe(2);
    expect(breakdown[1].email).toBe('bob@test.com');
    expect(breakdown[1].count).toBe(2);
  });

  it('uses salesperson_name when available, falls back to email', () => {
    const breakdown = getSalespersonBreakdown(jobs as any);
    expect(breakdown[0].name).toBe('Alice Smith');
    expect(breakdown[1].name).toBe('Bob Jones');
  });

  it('returns empty array for empty input', () => {
    expect(getSalespersonBreakdown([])).toEqual([]);
  });
});

describe('getIndustryBreakdown', () => {
  const jobs = [
    { job_id: '1', result_data: { industry: 'Technology' } },
    { job_id: '2', result_data: { industry: 'Technology' } },
    { job_id: '3', result_data: { industry: 'Finance' } },
    { job_id: '4', result_data: null },
    { job_id: '5' },
  ];

  it('counts industries from result_data', () => {
    const breakdown = getIndustryBreakdown(jobs as any);
    expect(breakdown).toContainEqual({ industry: 'Technology', count: 2 });
    expect(breakdown).toContainEqual({ industry: 'Finance', count: 1 });
  });

  it('ignores jobs without result_data or industry', () => {
    const breakdown = getIndustryBreakdown(jobs as any);
    expect(breakdown).toHaveLength(2);
  });

  it('sorts by count descending', () => {
    const breakdown = getIndustryBreakdown(jobs as any);
    expect(breakdown[0].industry).toBe('Technology');
    expect(breakdown[0].count).toBe(2);
  });

  it('returns empty array for empty input', () => {
    expect(getIndustryBreakdown([])).toEqual([]);
  });
});
