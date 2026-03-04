/**
 * Tests for useJobs hook — localStorage quota handling.
 * TDD: These tests verify that the jobs provider handles localStorage
 * quota exceeded errors gracefully and excludes bulky result data.
 */

import { renderHook, act } from '@testing-library/react';
import { JobsProvider, useJobs } from '../useJobs';
import type { ReactNode } from 'react';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  let quotaExceeded = false;
  return {
    getItem: jest.fn((key: string) => store[key] ?? null),
    setItem: jest.fn((key: string, value: string) => {
      if (quotaExceeded) {
        throw new DOMException(
          "Failed to execute 'setItem' on 'Storage': Setting the value of '" +
            key +
            "' exceeded the quota.",
          'QuotaExceededError'
        );
      }
      store[key] = value;
    }),
    removeItem: jest.fn((key: string) => { delete store[key]; }),
    clear: jest.fn(() => { store = {}; }),
    setQuotaExceeded: (val: boolean) => { quotaExceeded = val; },
    _getStore: () => store,
  };
})();

Object.defineProperty(window, 'localStorage', { value: localStorageMock });

function wrapper({ children }: { children: ReactNode }) {
  return <JobsProvider>{children}</JobsProvider>;
}

describe('useJobs localStorage handling', () => {
  beforeEach(() => {
    localStorageMock.clear();
    localStorageMock.setQuotaExceeded(false);
    jest.clearAllMocks();
  });

  it('should not crash when localStorage.setItem throws QuotaExceededError', () => {
    const { result } = renderHook(() => useJobs(), { wrapper });

    // Add a job, then simulate quota exceeded on next state change
    act(() => {
      result.current.addJob('job-1', {
        company_name: 'Test Co',
        domain: 'test.com',
        industry: 'Tech',
        requested_by: 'user@test.com',
      });
    });

    localStorageMock.setQuotaExceeded(true);

    // This should NOT throw — the hook should catch the error
    expect(() => {
      act(() => {
        result.current.updateJob('job-1', { status: 'processing', progress: 50 });
      });
    }).not.toThrow();

    // State should still be updated in memory
    expect(result.current.getJob('job-1')?.status).toBe('processing');
  });

  it('should not persist full result objects to localStorage', () => {
    const { result } = renderHook(() => useJobs(), { wrapper });

    act(() => {
      result.current.addJob('job-2', {
        company_name: 'Big Corp',
        domain: 'bigcorp.com',
        industry: 'Finance',
        requested_by: 'user@test.com',
      });
    });

    // Simulate a completed job with a large result
    const largeResult = {
      company_name: 'Big Corp',
      domain: 'bigcorp.com',
      executive_summary: 'A very large summary...',
      stakeholder_map: { contacts: new Array(50).fill({ name: 'Person', phone: '555-0100' }) },
      raw_data: { apiResponses: new Array(20).fill({ body: 'x'.repeat(10000) }) },
    };

    act(() => {
      result.current.updateJob('job-2', {
        status: 'completed',
        result: largeResult as never,
      });
    });

    // The in-memory state should have the result
    expect(result.current.getJob('job-2')?.result).toBeDefined();

    // But localStorage should NOT contain the full result
    const stored = localStorageMock._getStore()['radtest_jobs'];
    if (stored) {
      const parsed = JSON.parse(stored);
      const storedJob = parsed.find((j: { jobId: string }) => j.jobId === 'job-2');
      expect(storedJob.result).toBeUndefined();
    }
  });

  it('should cap stored jobs to prevent unbounded growth', () => {
    const { result } = renderHook(() => useJobs(), { wrapper });

    // Add more than the max limit of jobs
    for (let i = 0; i < 60; i++) {
      act(() => {
        result.current.addJob(`job-${i}`, {
          company_name: `Company ${i}`,
          domain: `company${i}.com`,
          industry: 'Tech',
          requested_by: 'user@test.com',
        });
      });
    }

    const stored = localStorageMock._getStore()['radtest_jobs'];
    if (stored) {
      const parsed = JSON.parse(stored);
      expect(parsed.length).toBeLessThanOrEqual(50);
    }
  });
});
