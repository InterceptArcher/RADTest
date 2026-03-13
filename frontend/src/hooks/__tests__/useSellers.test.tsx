/**
 * Tests for useSellers hook — seller CRUD and job counting.
 * TDD: These tests verify that sellers can be created, listed,
 * and that monthly job counts are computed correctly.
 */

import { renderHook, act } from '@testing-library/react';
import { SellersProvider, useSellers } from '../useSellers';
import type { ReactNode } from 'react';

// Mock Supabase client
jest.mock('@/lib/supabase', () => ({
  supabase: {
    from: jest.fn(() => ({
      select: jest.fn(() => ({
        order: jest.fn(() => Promise.resolve({ data: [], error: null })),
      })),
      insert: jest.fn(() => ({
        select: jest.fn(() => ({
          single: jest.fn(() =>
            Promise.resolve({
              data: { id: 'seller-1', name: 'Acme Corp', created_at: new Date().toISOString() },
              error: null,
            })
          ),
        })),
      })),
      delete: jest.fn(() => ({
        eq: jest.fn(() => Promise.resolve({ error: null })),
      })),
    })),
    channel: jest.fn(() => ({
      on: jest.fn().mockReturnThis(),
      subscribe: jest.fn(),
    })),
    removeChannel: jest.fn(),
  },
}));

function wrapper({ children }: { children: ReactNode }) {
  return <SellersProvider>{children}</SellersProvider>;
}

describe('useSellers', () => {
  it('should initialize with empty sellers list', () => {
    const { result } = renderHook(() => useSellers(), { wrapper });
    expect(result.current.sellers).toEqual([]);
  });

  it('should create a new seller', async () => {
    const { result } = renderHook(() => useSellers(), { wrapper });

    await act(async () => {
      await result.current.createSeller('Acme Corp');
    });

    expect(result.current.sellers.length).toBe(1);
    expect(result.current.sellers[0].name).toBe('Acme Corp');
  });

  it('should compute monthly job count for a seller', () => {
    const { result } = renderHook(() => useSellers(), { wrapper });

    const now = new Date();
    const thisMonth = now.toISOString();
    const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 15).toISOString();

    const count = result.current.getMonthlyJobCount('seller-1', [
      { jobId: '1', sellerId: 'seller-1', createdAt: thisMonth },
      { jobId: '2', sellerId: 'seller-1', createdAt: thisMonth },
      { jobId: '3', sellerId: 'seller-1', createdAt: lastMonth },
      { jobId: '4', sellerId: 'seller-2', createdAt: thisMonth },
    ]);

    expect(count).toBe(2);
  });
});
