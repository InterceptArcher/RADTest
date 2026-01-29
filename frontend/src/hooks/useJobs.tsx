'use client';

import { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react';
import type { JobWithMetadata, ProfileResult, CompanyProfileRequest } from '@/types';
import { apiClient } from '@/lib/api';

interface JobsContextType {
  jobs: JobWithMetadata[];
  addJob: (jobId: string, request: CompanyProfileRequest) => void;
  updateJob: (jobId: string, updates: Partial<JobWithMetadata>) => void;
  removeJob: (jobId: string) => void;
  getJob: (jobId: string) => JobWithMetadata | undefined;
  activeJobIds: string[];
}

const JobsContext = createContext<JobsContextType | undefined>(undefined);

const STORAGE_KEY = 'radtest_jobs';

export function JobsProvider({ children }: { children: ReactNode }) {
  const [jobs, setJobs] = useState<JobWithMetadata[]>([]);

  // Load jobs from localStorage on mount
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

  // Save jobs to localStorage when they change
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(jobs));
  }, [jobs]);

  const addJob = useCallback((jobId: string, request: CompanyProfileRequest) => {
    const newJob: JobWithMetadata = {
      jobId,
      companyName: request.company_name,
      domain: request.domain,
      industry: request.industry,
      status: 'pending',
      progress: 0,
      currentStep: 'Queued...',
      createdAt: new Date().toISOString(),
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
    setJobs((prev) => prev.filter((job) => job.jobId !== jobId));
  }, []);

  const getJob = useCallback((jobId: string) => {
    return jobs.find((job) => job.jobId === jobId);
  }, [jobs]);

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

// Hook to poll active jobs
export function useJobPolling() {
  const { activeJobIds, updateJob } = useJobs();

  useEffect(() => {
    if (activeJobIds.length === 0) return;

    const pollJobs = async () => {
      for (const jobId of activeJobIds) {
        try {
          const status = await apiClient.checkJobStatus(jobId);
          updateJob(jobId, {
            status: status.status,
            progress: status.progress ?? 0,
            currentStep: status.current_step ?? 'Processing...',
            result: status.result,
            completedAt: status.status === 'completed' ? new Date().toISOString() : undefined,
          });
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
  }, [activeJobIds, updateJob]);
}
