'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useJobs } from '@/hooks/useJobs';
import { activeStage, STAGES } from '@/lib/stages';

function ago(iso?: string): string {
  if (!iso) return '';
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return 'now';
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  if (s < 86400) return `${Math.floor(s / 3600)}h`;
  return `${Math.floor(s / 86400)}d`;
}
const cost = (j: any) => (j.result as any)?.api_cost?.total_usd as number | undefined;
const contacts = (j: any) => {
  const sc = (j.result as any)?.slide_contacts;
  if (!sc) return undefined;
  return Object.values(sc).reduce((n: number, v: any) => n + (Array.isArray(v) ? v.filter((c: any) => !c.is_sentinel).length : 0), 0);
};

type Filter = 'all' | 'processing' | 'completed' | 'failed';

export default function JobsPage() {
  const router = useRouter();
  const { jobs } = useJobs();
  const [filter, setFilter] = useState<Filter>('all');

  const counts = {
    all: jobs.length,
    processing: jobs.filter((j) => j.status === 'processing' || j.status === 'pending').length,
    completed: jobs.filter((j) => j.status === 'completed').length,
    failed: jobs.filter((j) => j.status === 'failed').length,
  };
  const totalSpend = jobs.reduce((a, j) => a + (cost(j) || 0), 0);
  const shown = jobs.filter((j) =>
    filter === 'all' ? true : filter === 'processing' ? (j.status === 'processing' || j.status === 'pending') : j.status === filter);

  const chip = (f: Filter, label: string) => (
    <span className={'f' + (filter === f ? ' on' : '')} onClick={() => setFilter(f)}>{label} · {counts[f]}</span>
  );

  return (
    <>
      <div className="filters">
        {chip('all', 'All')}{chip('processing', 'Running')}{chip('completed', 'Completed')}{chip('failed', 'Failed')}
        <span className="f" style={{ marginLeft: 'auto' }}>Total spend · ${totalSpend.toFixed(2)}</span>
      </div>
      <div className="panel"><div className="pb" style={{ paddingTop: 14 }}>
        <table>
          <thead><tr><th>Company</th><th>Domain</th><th>Seller</th><th>Status</th><th>Stage</th><th>Contacts</th><th>Cost</th><th>Created</th><th>Deck</th></tr></thead>
          <tbody>
            {shown.length === 0 && <tr><td colSpan={9} style={{ color: 'var(--faint)' }}>No jobs match this filter.</td></tr>}
            {shown.map((j) => {
              const act = activeStage(j.progress, j.status);
              const url = (j.result as any)?.slideshow_url;
              return (
                <tr key={j.jobId} style={{ cursor: 'pointer' }} onClick={() => router.push(`/dashboard/jobs/${j.jobId}`)}>
                  <td><b>{j.companyName}</b></td>
                  <td>{j.domain}</td>
                  <td>{j.sellerName || '—'}</td>
                  <td><span className={'badge ' + (j.status === 'completed' ? 'done' : j.status === 'failed' ? 'fail' : 'run')}><span className="d" />{j.status === 'completed' ? 'Done' : j.status === 'failed' ? 'Failed' : 'Running'}</span></td>
                  <td>{j.status === 'completed' ? '9/9' : `${act + 1}/9 ${STAGES[act].label}`}</td>
                  <td>{contacts(j) ?? '—'}</td>
                  <td className="cost">${(cost(j) || 0).toFixed(2)}</td>
                  <td>{ago(j.createdAt)}</td>
                  <td>{url ? <a className="lk2" style={{ border: 0, padding: 0 }} href={url} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>↗ pptx</a> : '—'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div></div>
    </>
  );
}
