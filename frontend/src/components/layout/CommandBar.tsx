'use client';

import { useMemo, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useJobs } from '@/hooks/useJobs';
import { useNotifications, toNotifications, type JobNotification } from '@/lib/notifications';

function ago(iso: string): string {
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return 'now';
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  if (s < 86400) return `${Math.floor(s / 3600)}h`;
  return `${Math.floor(s / 86400)}d`;
}

export default function CommandBar() {
  const pathname = usePathname();
  const router = useRouter();
  const { jobs, getJob } = useJobs();
  const { dismissed, dismissAlert } = useNotifications();

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

  // Finished-job notifications (completed + failed), newest first.
  const allNotifs = useMemo(() => toNotifications(jobs), [jobs]);
  // Badge counts only alerts the user hasn't flagged (hovered) yet.
  const alertCount = allNotifs.filter((n) => !dismissed.has(n.jobId)).length;

  const [open, setOpen] = useState(false);
  // Snapshot the visible list when the dropdown opens, so hovering (which marks
  // an alert seen) doesn't pull the row out from under the cursor mid-session.
  // Flagged rows still drop out the next time the dropdown is opened.
  const [snapshot, setSnapshot] = useState<JobNotification[]>([]);

  const toggleBell = () => {
    setOpen((prev) => {
      const next = !prev;
      if (next) setSnapshot(allNotifs.filter((n) => !dismissed.has(n.jobId)).slice(0, 25));
      return next;
    });
  };

  const openInbox = (jobId: string) => {
    dismissAlert(jobId);
    setOpen(false);
    router.push('/dashboard');
  };

  return (
    <header className="bar">
      <span className="title">{title} <small>{sub}</small></span>
      <div className="telem">
        <span className="chip"><span className="live-dot" /><b>{running}</b> running</span>
        <span className="chip">today <b>${spend.toFixed(2)}</b></span>
        <div className="bellwrap">
          <button type="button" className="chip bell" onClick={toggleBell} aria-label="Notifications" aria-expanded={open}>
            ⚠ <b>{alertCount}</b> alerts
          </button>
          {open && (
            <>
              <div className="notif-backdrop" onClick={() => setOpen(false)} />
              <div className="notif-dd" role="menu">
                <div className="notif-hd">Finished jobs</div>
                {snapshot.length === 0 && <div className="notif-empty">no new notifications</div>}
                {snapshot.map((n) => (
                  <div
                    key={n.jobId}
                    className={'notif ' + (n.kind === 'completed' ? 'ok' : 'bad')}
                    role="menuitem"
                    tabIndex={0}
                    onMouseEnter={() => dismissAlert(n.jobId)}
                    onClick={() => openInbox(n.jobId)}
                  >
                    <span className="ni">{n.kind === 'completed' ? '✓' : '✕'}</span>
                    <span className="nt">
                      <b>{n.companyName}</b> {n.kind === 'completed' ? 'deck ready' : 'failed'}
                    </span>
                    <span className="nw">{ago(n.at)}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
