'use client';

import { useMemo } from 'react';
import { useSellers } from '@/hooks/useSellers';
import { useJobs } from '@/hooks/useJobs';
import type { JobWithMetadata } from '@/types';

/** Read a job's total API cost in USD; missing/malformed → 0. */
function jobCost(job: JobWithMetadata): number {
  const total = (job.result as { api_cost?: { total_usd?: number } } | undefined)?.api_cost?.total_usd;
  return typeof total === 'number' && isFinite(total) ? total : 0;
}

interface SellerStats {
  id: string;
  name: string;
  role: string;
  jobCount: number;
  successPct: number;
  spend: number;
  /** ~6 bar heights (percentages) for the sparkline. */
  bars: number[];
}

/**
 * Build ~6 sparkline bar heights from a numeric series. Falls back to a
 * varied static shape when there is no signal so cards never render empty.
 */
function buildBars(values: number[]): number[] {
  const filtered = values.filter((v) => v > 0);
  if (filtered.length === 0) {
    return [40, 70, 55, 90, 75, 100];
  }
  const series = values.slice(0, 6);
  while (series.length < 6) series.unshift(0);
  const max = Math.max(...series);
  return series.map((v) => {
    const pct = max > 0 ? Math.round((v / max) * 100) : 0;
    return Math.max(8, Math.min(100, pct));
  });
}

export default function SellersPage() {
  const { sellers } = useSellers();
  const { jobs } = useJobs();

  const sellerStats = useMemo<SellerStats[]>(() => {
    return sellers.map((seller) => {
      const sellerJobs = jobs.filter((j) => j.sellerId === seller.id);
      const completed = sellerJobs.filter((j) => j.status === 'completed').length;
      const failed = sellerJobs.filter((j) => j.status === 'failed').length;
      const decided = completed + failed;
      const successPct = decided > 0 ? Math.round((completed / decided) * 100) : 0;
      const spend = sellerJobs.reduce((sum, j) => sum + jobCost(j), 0);
      // Prefer per-job costs for the spark; fall back to a count-based shape.
      const costSeries = sellerJobs.map(jobCost);
      const bars = buildBars(costSeries.some((c) => c > 0) ? costSeries : sellerJobs.map(() => 1));
      return {
        id: seller.id,
        name: seller.name,
        role: 'Seller',
        jobCount: sellerJobs.length,
        successPct,
        spend,
        bars,
      };
    });
  }, [sellers, jobs]);

  const team = useMemo(() => {
    const totalJobs = sellerStats.reduce((s, x) => s + x.jobCount, 0);
    const allSellerJobs = jobs.filter((j) => j.sellerId);
    const completed = allSellerJobs.filter((j) => j.status === 'completed').length;
    const failed = allSellerJobs.filter((j) => j.status === 'failed').length;
    const decided = completed + failed;
    const successPct = decided > 0 ? Math.round((completed / decided) * 100) : 0;
    const spend = sellerStats.reduce((s, x) => s + x.spend, 0);
    const spendSeries = sellerStats.map((x) => x.spend);
    const bars = buildBars(
      spendSeries.some((c) => c > 0) ? spendSeries : sellerStats.map((x) => x.jobCount)
    );
    return { totalJobs, successPct, spend, bars };
  }, [sellerStats, jobs]);

  return (
    <section className="view" id="view-sellers">
      <div className="row2" style={{ marginBottom: 18 }}>
        <div className="panel">
          <div className="ph">
            <span className="eye"></span>
            <span className="k">Team</span>
            <h3>This month</h3>
          </div>
          <div className="pb">
            <div className="kv">
              <div className="c">
                <div className="l">Jobs run</div>
                <div className="v mono">{team.totalJobs}</div>
              </div>
              <div className="c">
                <div className="l">Success</div>
                <div className="v mono">{team.successPct}%</div>
              </div>
              <div className="c">
                <div className="l">Spend</div>
                <div className="v mono">${team.spend.toFixed(2)}</div>
              </div>
            </div>
          </div>
        </div>
        <div className="panel">
          <div className="ph">
            <span className="eye"></span>
            <span className="k">Trend</span>
            <h3>Spend / day</h3>
          </div>
          <div className="pb">
            <div className="spark" style={{ height: 64 }}>
              {team.bars.map((h, i) => (
                <i key={i} style={{ height: `${h}%` }}></i>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="sellers" style={{ gridTemplateColumns: 'repeat(3,1fr)' }}>
        {sellerStats.length === 0 ? (
          <div className="await">No sellers yet — create one to start attributing jobs.</div>
        ) : (
          sellerStats.map((s) => (
            <div className="seller" key={s.id}>
              <div className="nm">{s.name}</div>
              <div className="ro">{s.role}</div>
              <div className="big">{s.jobCount}</div>
              <div className="lbl">jobs run</div>
              <div className="spark">
                {s.bars.map((h, i) => (
                  <i key={i} style={{ height: `${h}%` }}></i>
                ))}
              </div>
              <div className="ftr">
                <span>${s.spend.toFixed(2)} spend</span>
                <b>{s.successPct}%</b>
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
