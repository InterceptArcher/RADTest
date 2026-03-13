'use client';

import { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react';
import { supabase } from '@/lib/supabase';
import type { Seller, SellerJob } from '@/types';

interface SellersContextType {
  sellers: Seller[];
  sellerJobs: SellerJob[];
  loading: boolean;
  createSeller: (name: string) => Promise<Seller | null>;
  deleteSeller: (id: string) => Promise<void>;
  addSellerJob: (job: SellerJob) => Promise<void>;
  updateSellerJob: (jobId: string, updates: Partial<SellerJob>) => void;
  getSellerJobs: (sellerId: string) => SellerJob[];
  getMonthlyJobCount: (sellerId: string, jobs?: { jobId?: string; job_id?: string; sellerId?: string; seller_id?: string; createdAt?: string; created_at?: string }[]) => number;
}

const SellersContext = createContext<SellersContextType | undefined>(undefined);

export function SellersProvider({ children }: { children: ReactNode }) {
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [sellerJobs, setSellerJobs] = useState<SellerJob[]>([]);
  const [loading, setLoading] = useState(true);

  // Fetch sellers from Supabase on mount
  useEffect(() => {
    const fetchSellers = async () => {
      try {
        const { data, error } = await supabase
          .from('sellers')
          .select('*')
          .order('created_at', { ascending: false });

        if (error) {
          console.error('Failed to fetch sellers:', error);
        } else if (data) {
          setSellers(data);
        }
      } catch (e) {
        console.error('Failed to fetch sellers:', e);
      }
    };

    const fetchSellerJobs = async () => {
      try {
        const { data, error } = await supabase
          .from('seller_jobs')
          .select('*')
          .order('created_at', { ascending: false });

        if (error) {
          console.error('Failed to fetch seller jobs:', error);
        } else if (data) {
          setSellerJobs(data);
        }
      } catch (e) {
        console.error('Failed to fetch seller jobs:', e);
      } finally {
        setLoading(false);
      }
    };

    fetchSellers();
    fetchSellerJobs();
  }, []);

  // Subscribe to real-time changes for sellers and seller_jobs
  useEffect(() => {
    const sellersChannel = supabase
      .channel('sellers-changes')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'sellers' }, (payload) => {
        if (payload.eventType === 'INSERT') {
          setSellers((prev) => {
            if (prev.some((s) => s.id === (payload.new as Seller).id)) return prev;
            return [payload.new as Seller, ...prev];
          });
        } else if (payload.eventType === 'DELETE') {
          setSellers((prev) => prev.filter((s) => s.id !== payload.old.id));
        }
      })
      .subscribe();

    const jobsChannel = supabase
      .channel('seller-jobs-changes')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'seller_jobs' }, (payload) => {
        if (payload.eventType === 'INSERT') {
          setSellerJobs((prev) => {
            if (prev.some((j) => j.id === (payload.new as SellerJob).id)) return prev;
            return [payload.new as SellerJob, ...prev];
          });
        } else if (payload.eventType === 'UPDATE') {
          setSellerJobs((prev) =>
            prev.map((j) => (j.id === (payload.new as SellerJob).id ? (payload.new as SellerJob) : j))
          );
        } else if (payload.eventType === 'DELETE') {
          setSellerJobs((prev) => prev.filter((j) => j.id !== payload.old.id));
        }
      })
      .subscribe();

    return () => {
      supabase.removeChannel(sellersChannel);
      supabase.removeChannel(jobsChannel);
    };
  }, []);

  const createSeller = useCallback(async (name: string): Promise<Seller | null> => {
    try {
      const { data, error } = await supabase
        .from('sellers')
        .insert({ name })
        .select()
        .single();

      if (error) {
        console.error('Failed to create seller:', error);
        return null;
      }

      // Optimistic update (real-time will also fire)
      setSellers((prev) => {
        if (prev.some((s) => s.id === data.id)) return prev;
        return [data, ...prev];
      });
      return data;
    } catch (e) {
      console.error('Failed to create seller:', e);
      return null;
    }
  }, []);

  const deleteSeller = useCallback(async (id: string) => {
    try {
      const { error } = await supabase.from('sellers').delete().eq('id', id);
      if (error) {
        console.error('Failed to delete seller:', error);
        return;
      }
      setSellers((prev) => prev.filter((s) => s.id !== id));
    } catch (e) {
      console.error('Failed to delete seller:', e);
    }
  }, []);

  const addSellerJob = useCallback(async (job: SellerJob) => {
    try {
      const { error } = await supabase.from('seller_jobs').insert({
        job_id: job.job_id,
        seller_id: job.seller_id,
        company_name: job.company_name,
        domain: job.domain,
        status: job.status,
        requested_by: job.requested_by,
        salesperson_name: job.salesperson_name,
        created_at: job.created_at,
      });

      if (error) {
        console.error('Failed to add seller job:', error);
      }
    } catch (e) {
      console.error('Failed to add seller job:', e);
    }
  }, []);

  const updateSellerJob = useCallback((jobId: string, updates: Partial<SellerJob>) => {
    // Update in Supabase
    supabase
      .from('seller_jobs')
      .update(updates)
      .eq('job_id', jobId)
      .then(({ error }) => {
        if (error) console.error('Failed to update seller job:', error);
      });

    // Optimistic local update
    setSellerJobs((prev) =>
      prev.map((j) => (j.job_id === jobId ? { ...j, ...updates } : j))
    );
  }, []);

  const getSellerJobs = useCallback(
    (sellerId: string) => {
      return sellerJobs.filter((j) => j.seller_id === sellerId);
    },
    [sellerJobs]
  );

  const getMonthlyJobCount = useCallback(
    (sellerId: string, jobsList?: { jobId?: string; job_id?: string; sellerId?: string; seller_id?: string; createdAt?: string; created_at?: string }[]) => {
      const now = new Date();
      const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);

      const jobs = jobsList || sellerJobs;
      return jobs.filter((j) => {
        const sid = ('seller_id' in j ? j.seller_id : (j as any).sellerId) as string;
        const createdAt = ('created_at' in j ? j.created_at : (j as any).createdAt) as string;
        return sid === sellerId && new Date(createdAt) >= startOfMonth;
      }).length;
    },
    [sellerJobs]
  );

  return (
    <SellersContext.Provider
      value={{
        sellers,
        sellerJobs,
        loading,
        createSeller,
        deleteSeller,
        addSellerJob,
        updateSellerJob,
        getSellerJobs,
        getMonthlyJobCount,
      }}
    >
      {children}
    </SellersContext.Provider>
  );
}

export function useSellers() {
  const context = useContext(SellersContext);
  if (context === undefined) {
    throw new Error('useSellers must be used within a SellersProvider');
  }
  return context;
}
