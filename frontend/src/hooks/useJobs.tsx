'use client';

import { createContext, useContext, useState, useCallback, useEffect, useRef, ReactNode } from 'react';
import type { JobWithMetadata, CompanyProfileRequest } from '@/types';
import { apiClient } from '@/lib/api';
import { supabase } from '@/lib/supabase';

interface JobsContextType {
  jobs: JobWithMetadata[];
  addJob: (jobId: string, request: CompanyProfileRequest, sellerId?: string, sellerName?: string) => void;
  updateJob: (jobId: string, updates: Partial<JobWithMetadata>) => void;
  removeJob: (jobId: string) => void;
  getJob: (jobId: string) => JobWithMetadata | undefined;
  activeJobIds: string[];
  fetchJobFromSupabase: (jobId: string) => Promise<JobWithMetadata | null>;
}

const JobsContext = createContext<JobsContextType | undefined>(undefined);

const STORAGE_KEY = 'radtest_jobs';
const MAX_STORED_JOBS = 50;

/**
 * Strip bulky result data before persisting to localStorage.
 * Only job metadata (id, status, timestamps) is stored.
 */
function toStorable(jobs: JobWithMetadata[]): JobWithMetadata[] {
  return jobs.slice(0, MAX_STORED_JOBS).map(({ result, ...meta }) => meta as JobWithMetadata);
}

/**
 * Convert a Supabase seller_job row into a JobWithMetadata object.
 */
function sellerJobToMetadata(
  sj: any,
  sellerName?: string
): JobWithMetadata {
  return {
    jobId: sj.job_id,
    companyName: sj.company_name,
    domain: sj.domain,
    status: sj.status,
    progress: sj.status === 'completed' ? 100 : sj.status === 'failed' ? 0 : 50,
    currentStep: sj.status === 'completed' ? 'Done' : sj.status === 'failed' ? 'Failed' : 'Processing...',
    createdAt: sj.created_at,
    completedAt: sj.completed_at || undefined,
    sellerId: sj.seller_id,
    sellerName: sellerName || undefined,
    requestedBy: sj.requested_by,
    salespersonName: sj.salesperson_name || undefined,
    result: sj.result_data || undefined,
  };
}

export function JobsProvider({ children }: { children: ReactNode }) {
  const [jobs, setJobs] = useState<JobWithMetadata[]>([]);
  const sellerJobsLoaded = useRef(false);

  // Load local jobs from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        setJobs(parsed);
      } catch (e) {
        console.error('Failed to parse stored jobs:', e);
      }
    }
  }, []);

  // Load seller jobs from Supabase on mount and merge with local jobs
  useEffect(() => {
    if (sellerJobsLoaded.current) return;
    sellerJobsLoaded.current = true;

    const loadSellerJobs = async () => {
      try {
        // Fetch all seller jobs
        const { data: sellerJobs, error } = await supabase
          .from('seller_jobs')
          .select('*')
          .order('created_at', { ascending: false });

        if (error || !sellerJobs || sellerJobs.length === 0) return;

        // Fetch seller names for these jobs
        const sellerIds = [...new Set(sellerJobs.map((sj: any) => sj.seller_id))];
        const { data: sellers } = await supabase
          .from('sellers')
          .select('*')
          .in('id', sellerIds);

        const sellerMap = new Map<string, string>();
        if (sellers) {
          for (const s of sellers) {
            sellerMap.set(s.id, s.name);
          }
        }

        // Convert to JobWithMetadata and merge (dedup by jobId, local takes priority)
        const remoteJobs = sellerJobs.map((sj: any) =>
          sellerJobToMetadata(sj, sellerMap.get(sj.seller_id))
        );

        setJobs((prev) => {
          const localJobIds = new Set(prev.map((j) => j.jobId));
          const newRemoteJobs = remoteJobs.filter(
            (rj: JobWithMetadata) => !localJobIds.has(rj.jobId)
          );
          if (newRemoteJobs.length === 0) return prev;
          return [...prev, ...newRemoteJobs];
        });
      } catch (e) {
        console.error('Failed to load seller jobs from Supabase:', e);
      }
    };

    loadSellerJobs();
  }, []);

  // Subscribe to real-time seller_jobs changes so other devices' jobs appear
  useEffect(() => {
    const channel = supabase
      .channel('seller-jobs-sync')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'seller_jobs' }, async (payload) => {
        if (payload.eventType === 'INSERT' || payload.eventType === 'UPDATE') {
          const sj = payload.new as any;

          // Look up seller name
          let sellerName: string | undefined;
          const { data: seller } = await supabase
            .from('sellers')
            .select('name')
            .eq('id', sj.seller_id)
            .single();
          if (seller) sellerName = seller.name;

          const job = sellerJobToMetadata(sj, sellerName);

          setJobs((prev) => {
            const idx = prev.findIndex((j) => j.jobId === job.jobId);
            if (idx >= 0) {
              const existing = prev[idx];
              const merged = {
                ...existing,
                status: job.status,
                completedAt: job.completedAt || existing.completedAt,
                result: job.result || existing.result,
                sellerName: job.sellerName || existing.sellerName,
              };
              const updated = [...prev];
              updated[idx] = merged;
              return updated;
            }
            return [job, ...prev];
          });
        } else if (payload.eventType === 'DELETE') {
          const oldRow = payload.old as any;
          if (oldRow?.job_id) {
            setJobs((prev) => prev.filter((j) => j.jobId !== oldRow.job_id));
          }
        }
      })
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  // Save local-only jobs to localStorage when they change
  useEffect(() => {
    try {
      // Only persist non-seller jobs to localStorage (seller jobs come from Supabase)
      const localOnlyJobs = jobs.filter((j) => !j.sellerId);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(toStorable(localOnlyJobs)));
    } catch (e) {
      console.error('Failed to persist jobs to localStorage:', e);
    }
  }, [jobs]);

  const addJob = useCallback((jobId: string, request: CompanyProfileRequest, sellerId?: string, sellerName?: string) => {
    const newJob: JobWithMetadata = {
      jobId,
      companyName: request.company_name,
      domain: request.domain,
      industry: request.industry,
      status: 'pending',
      progress: 0,
      currentStep: 'Queued...',
      createdAt: new Date().toISOString(),
      sellerId,
      sellerName,
      requestedBy: request.requested_by,
      salespersonName: request.salesperson_name,
    };
    setJobs((prev) => [newJob, ...prev]);
  }, []);

  const updateJob = useCallback((jobId: string, updates: Partial<JobWithMetadata>) => {
    setJobs((prev) =>
      prev.map((job) =>
        job.jobId === jobId
          ? { ...job, ...updates }
          : job
      )
    );
  }, []);

  const removeJob = useCallback((jobId: string) => {
    // Check if this is a seller job before removing from state
    setJobs((prev) => {
      const job = prev.find((j) => j.jobId === jobId);
      if (job?.sellerId) {
        // Delete from Supabase so it's removed across all devices
        supabase
          .from('seller_jobs')
          .delete()
          .eq('job_id', jobId)
          .then(({ error }) => {
            if (error) console.error('Failed to delete seller job from Supabase:', error);
          });
      }
      return prev.filter((j) => j.jobId !== jobId);
    });
  }, []);

  const getJob = useCallback((jobId: string) => {
    return jobs.find((job) => job.jobId === jobId);
  }, [jobs]);

  /**
   * Fetch a single job from Supabase seller_jobs table.
   * Used when a job isn't found locally (e.g. opened on a different device).
   */
  const fetchJobFromSupabase = useCallback(async (jobId: string): Promise<JobWithMetadata | null> => {
    try {
      const { data: sj, error } = await supabase
        .from('seller_jobs')
        .select('*')
        .eq('job_id', jobId)
        .single();

      if (error || !sj) return null;

      // Look up seller name
      let sellerName: string | undefined;
      const { data: seller } = await supabase
        .from('sellers')
        .select('name')
        .eq('id', sj.seller_id)
        .single();
      if (seller) sellerName = seller.name;

      const job = sellerJobToMetadata(sj, sellerName);

      // Add to local state so subsequent getJob calls find it
      setJobs((prev) => {
        if (prev.some((j) => j.jobId === jobId)) return prev;
        return [job, ...prev];
      });

      return job;
    } catch (e) {
      console.error('Failed to fetch job from Supabase:', e);
      return null;
    }
  }, []);

  const activeJobIds = jobs
    .filter((job) => job.status === 'pending' || job.status === 'processing')
    .map((job) => job.jobId);

  return (
    <JobsContext.Provider
      value={{
        jobs,
        addJob,
        updateJob,
        removeJob,
        getJob,
        activeJobIds,
        fetchJobFromSupabase,
      }}
    >
      {children}
    </JobsContext.Provider>
  );
}

export function useJobs() {
  const context = useContext(JobsContext);
  if (context === undefined) {
    throw new Error('useJobs must be used within a JobsProvider');
  }
  return context;
}

// Hook to poll active jobs and sync seller job statuses + results to Supabase
export function useJobPolling() {
  const { activeJobIds, updateJob, jobs } = useJobs();

  useEffect(() => {
    if (activeJobIds.length === 0) return;

    const pollJobs = async () => {
      for (const jobId of activeJobIds) {
        try {
          const status = await apiClient.checkJobStatus(jobId);
          const newStatus = status.status;
          const completedAt = newStatus === 'completed' ? new Date().toISOString() : undefined;

          updateJob(jobId, {
            status: newStatus,
            progress: status.progress ?? 0,
            currentStep: status.current_step ?? 'Processing...',
            result: status.result,
            completedAt,
          });

          // Sync status + result to Supabase for seller-assigned jobs
          const job = jobs.find((j) => j.jobId === jobId);
          if (job?.sellerId && (newStatus === 'completed' || newStatus === 'failed')) {
            const updatePayload: Record<string, any> = {
              status: newStatus,
              completed_at: completedAt || new Date().toISOString(),
            };

            // Save result data to Supabase so other devices can access it
            if (newStatus === 'completed' && status.result) {
              updatePayload.result_data = status.result;
            }

            supabase
              .from('seller_jobs')
              .update(updatePayload)
              .eq('job_id', jobId)
              .then(({ error }) => {
                if (error) console.error('Failed to sync seller job to Supabase:', error);
              });
          }
        } catch (e) {
          console.error(`Failed to poll job ${jobId}:`, e);
        }
      }
    };

    // Poll immediately
    pollJobs();

    // Then poll every 2 seconds
    const interval = setInterval(pollJobs, 2000);

    return () => clearInterval(interval);
  }, [activeJobIds, updateJob, jobs]);
}
