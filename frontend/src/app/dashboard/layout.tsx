'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Rail from '@/components/layout/Rail';
import CommandBar from '@/components/layout/CommandBar';
import Background from '@/components/ui/Background';
import { JobsProvider, useJobPolling } from '@/hooks/useJobs';
import { SellersProvider } from '@/hooks/useSellers';
import { useAuth } from '@/lib/auth';

/**
 * Mounts the app-wide job poller. Must live INSIDE JobsProvider. This keeps
 * active jobs polling + syncing their completion (status + result_data) to
 * Supabase on every dashboard page — not just Home — so a job that finishes
 * while you're on the Job View (or any other tab) no longer shows as stale
 * "processing" elsewhere, and its result is durably persisted.
 */
function JobPollingMount() {
  useJobPolling();
  return null;
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAuthenticated) router.replace('/login');
  }, [loading, isAuthenticated, router]);

  if (loading || !isAuthenticated) {
    return (
      <>
        <Background />
        <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', position: 'relative', zIndex: 1 }}>
          <div className="await"><span className="d" /> loading…</div>
        </div>
      </>
    );
  }

  return (
    <SellersProvider>
      <JobsProvider>
        <JobPollingMount />
        <Background />
        <Rail />
        <div className="main">
          <CommandBar />
          <div className="canvas">{children}</div>
        </div>
      </JobsProvider>
    </SellersProvider>
  );
}
