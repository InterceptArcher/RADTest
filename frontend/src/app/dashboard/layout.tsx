'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Rail from '@/components/layout/Rail';
import CommandBar from '@/components/layout/CommandBar';
import Background from '@/components/ui/Background';
import { JobsProvider } from '@/hooks/useJobs';
import { SellersProvider } from '@/hooks/useSellers';
import { useAuth } from '@/lib/auth';

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
