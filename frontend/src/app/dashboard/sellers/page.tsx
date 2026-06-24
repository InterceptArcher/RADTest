'use client';

import { useMemo } from 'react';
import { useSellers } from '@/hooks/useSellers';
import { useJobs } from '@/hooks/useJobs';
import type { JobWithMetadata } from '@/types';

const MONTHLY_LIMIT = 40;

function jobCost(job: JobWithMetadata): number {
  const total = (job.result as { api_cost?: { total_usd?: number } } | undefined)?.api_cost?.total_usd;
  return typeof total === 'number' && isFinite(total) ? total : 0;
}

function buildBars(values: number[]): number[] {
  const series = values.slice(-6);
  while (series.length < 6) series.unshift(0);
  const max = Math.max(...series, 0);
  if (max <= 0) return [40, 70, 55, 90, 75, 100];
  return series.map((v) => Math.max(8, Math.min(100, Math.round((v / max) * 100))));
}

export default function SellersPage() {
  // Sellers are created automatically from the Salesperson field on the intake
  // form (the same name that's fed into the deck) — there is no manual add here.
  const { sellers, deleteSeller, getMonthlyJobCount } = useSellers();
  const { jobs } = useJobs();

  const stats = useMemo(() => sellers.map((seller) => {
    const sj = jobs.filter((j) => j.sellerId === seller.id);
    const completed = sj.filter((j) => j.status === 'completed').length;
    const failed = sj.filter((j) => j.status === 'failed').length;
    const decided = completed + failed;
    return {
      id: seller.id, name: seller.name,
      monthly: getMonthlyJobCount(seller.id, jobs as any),
      jobCount: sj.length,
      successPct: decided > 0 ? Math.round((completed / decided) * 100) : 0,
      spend: sj.reduce((s, j) => s + jobCost(j), 0),
      bars: buildBars(sj.map((j) => jobCost(j) || 1)),
    };
  }), [sellers, jobs, getMonthlyJobCount]);

  const team = useMemo(() => {
    const monthly = stats.reduce((s, x) => s + x.monthly, 0);
    const decided = jobs.filter((j) => j.sellerId && (j.status === 'completed' || j.status === 'failed'));
    const completed = decided.filter((j) => j.status === 'completed').length;
    return {
      monthly, sellers: stats.length,
      successPct: decided.length ? Math.round((completed / decided.length) * 100) : 0,
      spend: stats.reduce((s, x) => s + x.spend, 0),
      bars: buildBars(stats.map((x) => x.monthly)),
      spendBars: buildBars(stats.map((x) => x.spend)),
    };
  }, [stats, jobs]);

  const over = team.monthly > MONTHLY_LIMIT;
  const pct = Math.min(100, Math.round((team.monthly / MONTHLY_LIMIT) * 100));

  return (
    <>
      <div className="row2" style={{ marginBottom: 18, gridTemplateColumns: '1fr 1fr 1fr' }}>
        <div className="panel">
          <div className="ph"><span className="eye" /><span className="k">Team</span><h3>This month</h3></div>
          <div className="pb"><div className="kv">
            <div className="c"><div className="l">Sellers</div><div className="v mono">{team.sellers}</div></div>
            <div className="c"><div className="l">Success</div><div className="v mono">{team.successPct}%</div></div>
            <div className="c"><div className="l">Spend</div><div className="v mono">${team.spend.toFixed(2)}</div></div>
          </div></div>
        </div>
        {/* Spend trend (restored) */}
        <div className="panel">
          <div className="ph"><span className="eye" /><span className="k">Trend</span><h3>Spend by seller</h3></div>
          <div className="pb"><div className="spark" style={{ height: 64 }}>
            {team.spendBars.map((h, i) => <i key={i} style={{ height: `${h}%` }} />)}
          </div></div>
        </div>
        {/* GLOBAL monthly draw meter — across all sellers, overflow allowed, resets monthly */}
        <div className="panel">
          <div className="ph"><span className="eye" /><span className="k">Bandwidth</span><h3>Monthly draws</h3>
            <span className="n">resets {new Date(new Date().getFullYear(), new Date().getMonth() + 1, 1).toLocaleString('en', { month: 'short', day: 'numeric' })}</span></div>
          <div className="pb">
            <div className={'drawmeter' + (over ? ' over' : '')}>
              <div className="top2" style={{ fontSize: 11 }}><span>Profiles drawn this month</span><b style={{ fontSize: 20 }}>{team.monthly} / {MONTHLY_LIMIT}</b></div>
              <div className="drawbar" style={{ height: 12 }}><i style={{ width: `${pct}%` }} /></div>
              {over
                ? <div className="over-note">+{team.monthly - MONTHLY_LIMIT} over the {MONTHLY_LIMIT}/month guide</div>
                : <div className="over-note" style={{ color: 'var(--faint)' }}>{MONTHLY_LIMIT - team.monthly} draws remaining</div>}
            </div>
          </div>
        </div>
      </div>

      <div className="sellers" style={{ gridTemplateColumns: 'repeat(3,1fr)' }}>
        {stats.length === 0 && <div className="await">No sellers yet — they appear automatically when you enter a salesperson on a new profile.</div>}
        {stats.map((s) => (
          <div className="seller" key={s.id}>
            <button className="del" title="Remove seller" onClick={() => deleteSeller(s.id)}>×</button>
            <div className="nm">{s.name}</div>
            <div className="ro">Seller</div>
            <div className="big">{s.monthly}</div><div className="lbl">draws this month</div>
            <div className="spark">{s.bars.map((h, i) => <i key={i} style={{ height: `${h}%` }} />)}</div>
            <div className="ftr"><span>{s.jobCount} total · ${s.spend.toFixed(2)}</span><b>{s.successPct}%</b></div>
          </div>
        ))}
      </div>
    </>
  );
}
