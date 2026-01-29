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
      <div className="min-h-screen bg-gray-50">
        <Sidebar />
        <main className="pl-64">
          <div className="min-h-screen">
            {children}
          </div>
        </main>
      </div>
    </JobsProvider>
  );
}
