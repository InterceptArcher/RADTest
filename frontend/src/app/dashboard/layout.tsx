'use client';

import Sidebar from '@/components/layout/Sidebar';
import { JobsProvider } from '@/hooks/useJobs';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <JobsProvider>
      <div className="min-h-screen bg-slate-50">
        {/* Background pattern */}
        <div className="fixed inset-0 bg-gradient-mesh opacity-50 pointer-events-none" />

        <Sidebar />
        <main className="pl-72 relative">
          <div className="min-h-screen">
            {children}
          </div>
        </main>
      </div>
    </JobsProvider>
  );
}
