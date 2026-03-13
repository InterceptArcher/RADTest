'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Sidebar from '@/components/layout/Sidebar';
import NetworkBackground from '@/components/ui/NetworkBackground';
import { JobsProvider } from '@/hooks/useJobs';
import { SellersProvider } from '@/hooks/useSellers';
import { useAuth } from '@/lib/auth';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.replace('/login');
    }
  }, [loading, isAuthenticated, router]);

  if (loading || !isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F4F4F4]">
        <svg className="w-8 h-8 text-[#939393] animate-spin" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
      </div>
    );
  }

  return (
    <SellersProvider>
      <JobsProvider>
        <div className="min-h-screen bg-[#F4F4F4]">
          <Sidebar />
          {/* Network background */}
          <div className="fixed inset-0 pointer-events-none z-0 pl-56">
            <NetworkBackground className="w-full h-full text-[#282727]" opacity={0.035} />
          </div>
          <main className="pl-56 relative z-[1]">
            <div className="min-h-screen">
              {children}
            </div>
          </main>
        </div>
      </JobsProvider>
    </SellersProvider>
  );
}
