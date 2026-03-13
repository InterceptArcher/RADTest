/**
 * Tests for useJobs Supabase sync — seller jobs loaded from Supabase
 * and accessible on any device via fetchJobFromSupabase.
 * TDD: These tests verify that seller jobs merge into local state
 * and that individual jobs can be fetched from Supabase on demand.
 */

import { renderHook, act } from '@testing-library/react';

const mockSellerJobs = [
  {
    id: 'sj-1',
    job_id: 'remote-job-1',
    seller_id: 'seller-1',
    company_name: 'Remote Corp',
    domain: 'remotecorp.com',
    status: 'completed',
    requested_by: 'sales@test.com',
    salesperson_name: 'Jane',
    created_at: '2026-03-01T00:00:00Z',
    completed_at: '2026-03-01T01:00:00Z',
    result_data: { success: true, company_name: 'Remote Corp', domain: 'remotecorp.com', confidence_score: 0.9, validated_data: { company_name: 'Remote Corp', domain: 'remotecorp.com' } },
  },
];

const mockSellers = [
  { id: 'seller-1', name: 'Acme Seller', created_at: '2026-01-01T00:00:00Z' },
];

// Mock Supabase before importing useJobs
jest.mock('@/lib/supabase', () => ({
  supabase: {
    from: jest.fn((table: string) => {
      if (table === 'seller_jobs') {
        return {
          select: jest.fn(() => ({
            order: jest.fn(() => Promise.resolve({ data: mockSellerJobs, error: null })),
            eq: jest.fn(() => ({
              single: jest.fn(() => Promise.resolve({ data: mockSellerJobs[0], error: null })),
            })),
          })),
          update: jest.fn(() => ({
            eq: jest.fn(() => Promise.resolve({ error: null })),
          })),
        };
      }
      if (table === 'sellers') {
        return {
          select: jest.fn(() => ({
            in: jest.fn(() => Promise.resolve({ data: mockSellers, error: null })),
          })),
        };
      }
      return {
        update: jest.fn(() => ({
          eq: jest.fn(() => Promise.resolve({ error: null })),
        })),
      };
    }),
    channel: jest.fn(() => ({
      on: jest.fn().mockReturnThis(),
      subscribe: jest.fn(),
    })),
    removeChannel: jest.fn(),
  },
}));

import { JobsProvider, useJobs } from '../useJobs';
import type { ReactNode } from 'react';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: jest.fn((key: string) => store[key] ?? null),
    setItem: jest.fn((key: string, value: string) => { store[key] = value; }),
    removeItem: jest.fn((key: string) => { delete store[key]; }),
    clear: jest.fn(() => { store = {}; }),
  };
})();
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

function wrapper({ children }: { children: ReactNode }) {
  return <JobsProvider>{children}</JobsProvider>;
}

describe('useJobs Supabase sync', () => {
  beforeEach(() => {
    localStorageMock.clear();
    jest.clearAllMocks();
  });

  it('should load seller jobs from Supabase on mount and merge into jobs list', async () => {
    const { result } = renderHook(() => useJobs(), { wrapper });

    // Wait for async Supabase fetch to resolve
    await act(async () => {
      await new Promise((r) => setTimeout(r, 100));
    });

    const remoteJob = result.current.jobs.find((j) => j.jobId === 'remote-job-1');
    expect(remoteJob).toBeDefined();
    expect(remoteJob?.companyName).toBe('Remote Corp');
    expect(remoteJob?.sellerId).toBe('seller-1');
    expect(remoteJob?.result).toBeDefined();
  });

  it('should provide fetchJobFromSupabase to load individual jobs on demand', async () => {
    const { result } = renderHook(() => useJobs(), { wrapper });

    await act(async () => {
      await new Promise((r) => setTimeout(r, 100));
    });

    expect(result.current.fetchJobFromSupabase).toBeDefined();
  });
});
