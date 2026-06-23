/**
 * Live Job View (v3.1) — watch a job run in real time. Polls /job-status with
 * backoff, shows the 6-stage pipeline progress, partial data as it fills in, and
 * the debug log. Safe on legacy jobs (v3.1-only fields are read defensively).
 */
'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { apiClient } from '@/lib/api';
import type { JobStatus } from '@/types';
import ConfidenceBadge from '@/components/jobs/ConfidenceBadge';
import ContactCatalogue from '@/components/jobs/ContactCatalogue';

const STAGES = [
  { key: '1_resolution', label: 'Company resolution' },
  { key: '2_general', label: 'General intelligence' },
  { key: '3_contacts', label: 'Surgical contacts' },
  { key: '4_council', label: 'Council validation' },
  { key: '5_format', label: 'Slide copy' },
  { key: '6_render', label: 'Render deck' },
];

type Tab = 'progress' | 'data' | 'logs';

export default function LiveJobView({ params }: { params: { jobId: string } }) {
  const { jobId } = params;
  const [job, setJob] = useState<JobStatus | null>(null);
  const [tab, setTab] = useState<Tab>('progress');
  const [error, setError] = useState<string | null>(null);
  const [delay, setDelay] = useState(2000);

  const poll = useCallback(async () => {
    try {
      const status = await apiClient.checkJobStatus(jobId);
      setJob(status);
      setError(null);
      setDelay(2000);
      return status.status;
    } catch (e) {
      setError('Reconnecting…');
      setDelay((d) => Math.min(d * 2, 8000)); // backoff
      return null;
    }
  }, [jobId]);

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    const loop = async () => {
      const s = await poll();
      if (!active) return;
      if (s === 'completed' || s === 'failed') return; // stop polling on terminal
      timer = setTimeout(loop, delay);
    };
    loop();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [poll, delay]);

  const result = (job?.result ?? {}) as any;
  const currentStage: string | undefined = result.current_stage || (job as any)?.current_stage;
  const logs: any[] = result.debug_logs || (job as any)?.debug_logs || result.enrichment_trace || [];
  const reachedIndex = STAGES.findIndex((s) => s.key === currentStage);
  const isDone = job?.status === 'completed';
  const isFailed = job?.status === 'failed';

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900">Live job · {jobId}</h1>
        <Link href={`/dashboard/jobs/${jobId}`} className="text-sm text-[#024AD8] hover:underline">
          View details →
        </Link>
      </div>

      {error && <div className="mb-3 rounded bg-amber-50 px-3 py-2 text-sm text-amber-800">{error}</div>}

      <div className="mb-4 flex gap-2 border-b border-slate-200">
        {(['progress', 'data', 'logs'] as Tab[]).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-3 py-2 text-sm font-medium capitalize ${
              tab === t ? 'border-b-2 border-[#024AD8] text-slate-900' : 'text-slate-500'
            }`}>
            {t === 'data' ? 'Partial data' : t}
          </button>
        ))}
      </div>

      {tab === 'progress' && (
        <div className="space-y-2">
          <div className="mb-2 text-sm text-slate-600">{job?.current_step || 'Starting…'}</div>
          {STAGES.map((s, i) => {
            const reached = reachedIndex >= 0 ? i <= reachedIndex : false;
            const active = reachedIndex === i && !isDone;
            return (
              <div key={s.key} className="flex items-center gap-3">
                <span className={`flex h-6 w-6 items-center justify-center rounded-full text-xs ${
                  isDone || (reached && !active) ? 'bg-green-500 text-white'
                    : active ? 'bg-[#024AD8] text-white animate-pulse'
                    : 'bg-slate-200 text-slate-500'
                }`}>{isDone || (reached && !active) ? '✓' : i + 1}</span>
                <span className={active ? 'font-semibold text-slate-900' : 'text-slate-600'}>{s.label}</span>
              </div>
            );
          })}
          {isFailed && <div className="mt-3 rounded bg-red-50 px-3 py-2 text-sm text-red-800">
            Job failed{result.error_message ? `: ${result.error_message}` : ''}.</div>}
          {isDone && result.slideshow_url && (
            <a href={result.slideshow_url} target="_blank" rel="noopener noreferrer"
               className="btn-primary mt-4 inline-flex">Download Deck (.pptx)</a>
          )}
        </div>
      )}

      {tab === 'data' && (
        <div>
          <div className="mb-3"><ConfidenceBadge score={result.data_quality_score} /></div>
          {result.company_name && (
            <div className="card mb-4 p-3 text-sm">
              <span className="font-semibold">{result.company_name}</span>
              {result.industry && <span className="text-slate-500"> · {result.industry}</span>}
            </div>
          )}
          <ContactCatalogue catalogue={result.contact_catalogue} selected={result.slide_contacts} />
          {!result.contact_catalogue && (
            <div className="text-sm text-slate-400">Contacts will appear here as the pipeline runs.</div>
          )}
        </div>
      )}

      {tab === 'logs' && (
        <div className="max-h-[28rem] overflow-y-auto rounded border border-slate-200 bg-slate-50 p-3 font-mono text-xs">
          {logs.length === 0 && <div className="text-slate-400">No log entries yet.</div>}
          {logs.map((e, i) => (
            <div key={i} className="border-b border-slate-100 py-1">
              <span className="text-slate-400">{e.stage || e.source || ''}</span>{' '}
              <span className={e.level === 'error' ? 'text-red-600' : e.level === 'warn' ? 'text-amber-600' : 'text-slate-700'}>
                {e.msg || e.outcome || e.candidate_name || ''}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
