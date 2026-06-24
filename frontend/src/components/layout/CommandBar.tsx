'use client';

import { usePathname } from 'next/navigation';
import { useJobs } from '@/hooks/useJobs';

export default function CommandBar() {
  const pathname = usePathname();
  const { jobs, getJob } = useJobs();

  let title = 'Dashboard';
  let sub = '· today';
  if (pathname === '/dashboard/jobs') { title = 'Jobs'; sub = '· queue'; }
  else if (pathname.startsWith('/dashboard/jobs/')) {
    const id = pathname.split('/').pop() || '';
    title = getJob(id)?.companyName || 'Job'; sub = '· live';
  }
  else if (pathname.startsWith('/dashboard/sellers')) { title = 'Sellers'; sub = '· team'; }
  else if (pathname.startsWith('/dashboard/content-audit')) { title = 'Content Audit'; sub = ''; }
  else if (pathname.startsWith('/dashboard/docs')) { title = 'Documentation'; sub = ''; }

  const running = jobs.filter((j) => j.status === 'processing' || j.status === 'pending').length;
  const today = new Date().toDateString();
  const spend = jobs.reduce((s, j) => {
    const c = (j.result as any)?.api_cost?.total_usd;
    return new Date(j.createdAt).toDateString() === today && typeof c === 'number' ? s + c : s;
  }, 0);
  const alerts = jobs.filter((j) => {
    if (j.status !== 'completed' && j.status !== 'failed') return false;
    const t = j.completedAt || j.createdAt;
    return Date.now() - new Date(t).getTime() < 24 * 3600 * 1000;
  }).length;

  return (
    <header className="bar">
      <span className="title">{title} <small>{sub}</small></span>
      <div className="telem">
        <span className="chip"><span className="live-dot" /><b>{running}</b> running</span>
        <span className="chip">today <b>${spend.toFixed(2)}</b></span>
        <span className="chip bell">⚠ <b>{alerts}</b> alerts</span>
      </div>
    </header>
  );
}
