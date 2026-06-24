'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { apiClient } from '@/lib/api';
import { useJobs } from '@/hooks/useJobs';
import { useSellers } from '@/hooks/useSellers';
import { activeStage } from '@/lib/stages';

function elapsed(fromIso: string): string {
  const s = Math.max(0, Math.floor((Date.now() - new Date(fromIso).getTime()) / 1000));
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
}
function ago(iso?: string): string {
  if (!iso) return '';
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return 'now';
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  if (s < 86400) return `${Math.floor(s / 3600)}h`;
  return `${Math.floor(s / 86400)}d`;
}
const cost = (j: any) => (j.result as any)?.api_cost?.total_usd as number | undefined;
const contactCount = (j: any) => {
  const sc = (j.result as any)?.slide_contacts;
  if (!sc) return undefined;
  return Object.values(sc).reduce((n: number, v: any) => n + (Array.isArray(v) ? v.filter((c: any) => !c.is_sentinel).length : 0), 0);
};

export default function HomePage() {
  const router = useRouter();
  const { jobs, addJob } = useJobs();
  const { sellers, addSellerJob, createSeller } = useSellers();

  const [form, setForm] = useState({ company_name: '', domain: '', industry: '', requested_by: '', salesperson: '', canada_only: false });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  // Active-job polling is handled app-wide by useJobPolling() (mounted in the
  // dashboard layout), so the in-progress cards here stay live off the shared
  // jobs store without a duplicate poller.

  const set = (k: string, v: any) => setForm((f) => ({ ...f, [k]: v }));

  const launch = async () => {
    setError('');
    if (!form.company_name || !form.domain || !form.requested_by) { setError('Company, domain and requested-by are required.'); return; }
    setSubmitting(true);
    // The salesperson name IS the seller (and the name fed into the deck). Find an
    // existing seller by name (case-insensitive) or auto-create one — no manual
    // seller management.
    const spName = form.salesperson.trim();
    let seller = sellers.find((s) => s.name.trim().toLowerCase() === spName.toLowerCase());
    const req = {
      company_name: form.company_name, domain: form.domain, industry: form.industry || undefined,
      requested_by: form.requested_by, salesperson_name: spName || undefined, canada_only: form.canada_only,
    };
    try {
      if (!seller && spName) { try { seller = (await createSeller(spName)) || undefined; } catch { /* best-effort */ } }
      const res = await apiClient.submitProfileRequest(req);
      addJob(res.job_id, req, seller?.id, seller?.name || spName || undefined);
      if (seller) {
        await addSellerJob({
          job_id: res.job_id, seller_id: seller.id, company_name: form.company_name, domain: form.domain,
          status: 'processing', requested_by: form.requested_by, salesperson_name: seller.name, created_at: new Date().toISOString(),
        });
      }
      router.push(`/dashboard/jobs/${res.job_id}`);
    } catch (e: any) {
      setError(e?.message || 'Failed to launch'); setSubmitting(false);
    }
  };

  const inProgress = jobs.filter((j) => j.status === 'processing' || j.status === 'pending');
  const recent = jobs.slice(0, 6);
  const triage = jobs.filter((j) => j.status === 'completed' || j.status === 'failed').slice(0, 3);

  const sellerStats = sellers.slice(0, 4).map((s) => {
    const sj = jobs.filter((j) => j.sellerId === s.id);
    const done = sj.filter((j) => j.status === 'completed').length;
    const failed = sj.filter((j) => j.status === 'failed').length;
    const spend = sj.reduce((a, j) => a + (cost(j) || 0), 0);
    const rate = done + failed ? Math.round((done / (done + failed)) * 100) : 100;
    return { s, count: sj.length, spend, rate };
  });

  return (
    <div className="grid-home">
      <div className="col">
        <div className="panel"><div className="ph"><span className="eye" /><span className="k">01 · Intake</span><h3>New profile</h3></div>
          <div className="pb">
            <label>Company name</label><input className="inp" value={form.company_name} onChange={(e) => set('company_name', e.target.value)} placeholder="Microsoft" />
            <div className="two">
              <div><label>Domain</label><input className="inp" value={form.domain} onChange={(e) => set('domain', e.target.value)} placeholder="microsoft.com" /></div>
              <div><label>Industry</label><input className="inp" value={form.industry} onChange={(e) => set('industry', e.target.value)} placeholder="Technology" /></div>
            </div>
            <div className="two">
              <div><label>Requested by</label><input className="inp" value={form.requested_by} onChange={(e) => set('requested_by', e.target.value)} placeholder="you@intercept" /></div>
              <div><label>Salesperson</label><input className="inp" list="sellerlist" value={form.salesperson} onChange={(e) => set('salesperson', e.target.value)} placeholder="e.g. Jason Huang" />
                <datalist id="sellerlist">{sellers.map((s) => <option key={s.id} value={s.name} />)}</datalist>
              </div>
            </div>
            <div className="toggle"><span>Canada-only contacts</span>
              <div className={'sw' + (form.canada_only ? ' on' : '')} onClick={() => set('canada_only', !form.canada_only)} />
            </div>
            {error && <div className="err" style={{ height: 'auto', marginTop: 8 }}>{error}</div>}
            <button className="launch" onClick={launch} disabled={submitting}>{submitting ? 'Launching…' : '⚡ Launch profile'}</button>
          </div>
        </div>
        <div className="panel"><div className="ph"><span className="eye" /><span className="k">Triage</span><h3>Inbox</h3><span className="n">{triage.length} new</span></div>
          <div className="pb">
            {triage.length === 0 && <div className="await">no completed or failed jobs yet</div>}
            {triage.map((j) => (
              <div key={j.jobId} className={'alert ' + (j.status === 'completed' ? 'ok' : 'bad')}>
                <div className="ai">{j.status === 'completed' ? '✓' : '✕'}</div>
                <div className="at"><b>{j.companyName}</b> {j.status === 'completed' ? 'deck ready' : 'failed'}
                  <small>{j.status === 'completed' ? `${contactCount(j) ?? '—'} contacts · $${(cost(j) || 0).toFixed(2)}` : (j.currentStep || 'error')}</small></div>
                <Link className="go" href={`/dashboard/jobs/${j.jobId}`}>{j.status === 'completed' ? 'View' : 'Open'}</Link>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="col">
        <div className="panel"><div className="ph"><span className="eye" /><span className="k">Live</span><h3>In progress</h3><span className="n">{inProgress.length} jobs</span></div>
          <div className="pb">
            {inProgress.length === 0 && <div className="await">no jobs running — launch one to see it here live</div>}
            {inProgress.map((j) => {
              const act = activeStage(j.progress, j.status);
              return (
                <div key={j.jobId} className="jobc" onClick={() => router.push(`/dashboard/jobs/${j.jobId}`)}>
                  <div className="top"><b>{j.companyName}</b><span className="dom">{j.domain}</span><span className="meta">{elapsed(j.createdAt)} elapsed</span></div>
                  <div className="strip">{Array.from({ length: 9 }).map((_, i) => <i key={i} className={i < act ? 'done' : i === act ? 'act' : ''} />)}</div>
                  <div className="sub"><span className="st">▸ Stage {act + 1}/9 · {j.currentStep || 'Processing…'}</span><span className="ct">${(cost(j) || 0).toFixed(2)}</span></div>
                </div>
              );
            })}
          </div>
        </div>
        <div className="panel"><div className="ph"><span className="eye" /><span className="k">History</span><h3>Recent activity</h3><span className="n">synced · all devices</span></div>
          <div className="pb" style={{ paddingTop: 0 }}>
            <table>
              <thead><tr><th>Company</th><th>Seller</th><th>Status</th><th>Contacts</th><th>Cost</th><th>When</th></tr></thead>
              <tbody>
                {recent.length === 0 && <tr><td colSpan={6} style={{ color: 'var(--faint)' }}>No jobs yet.</td></tr>}
                {recent.map((j) => (
                  <tr key={j.jobId} style={{ cursor: 'pointer' }} onClick={() => router.push(`/dashboard/jobs/${j.jobId}`)}>
                    <td><b>{j.companyName}</b></td>
                    <td>{j.sellerName || '—'}</td>
                    <td><span className={'badge ' + (j.status === 'completed' ? 'done' : j.status === 'failed' ? 'fail' : 'run')}><span className="d" />{j.status === 'completed' ? 'Done' : j.status === 'failed' ? 'Failed' : 'Running'}</span></td>
                    <td>{contactCount(j) ?? '—'}</td>
                    <td className="cost">${(cost(j) || 0).toFixed(2)}</td>
                    <td>{ago(j.completedAt || j.createdAt)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="panel"><div className="ph"><span className="eye" /><span className="k">Team</span><h3>Seller overview</h3></div>
          <div className="pb"><div className="sellers">
            {sellerStats.length === 0 && <div className="await">no sellers yet — add one in the Sellers tab</div>}
            {sellerStats.map(({ s, count, spend, rate }) => (
              <div key={s.id} className="seller">
                <div className="nm">{s.name}</div><div className="ro">Seller</div>
                <div className="big">{count}</div><div className="lbl">jobs run</div>
                <div className="spark">{[40, 70, 55, 90, 75, 100].map((h, i) => <i key={i} style={{ height: `${h}%` }} />)}</div>
                <div className="ftr"><span>${spend.toFixed(2)}</span><b>{rate}%</b></div>
              </div>
            ))}
          </div></div>
        </div>
      </div>
    </div>
  );
}
