'use client';

import { useEffect, useRef, useState } from 'react';
import { apiClient } from '@/lib/api';
import { supabase } from '@/lib/supabase';

/** Live backend status (superset of the typed JobStatus — backend returns rich
 *  incremental fields like zoominfo_data, council_metadata, api_cost). */
export interface LiveStatus {
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  current_step?: string;
  result?: any;
  error?: string;
  api_cost?: any;
  [k: string]: any;
}

/**
 * Polls /job-status every ~1.5s while a job is processing, recording each
 * current_step transition into an audit log. Falls back to Supabase
 * result_data for already-finished jobs (cross-device / after a restart).
 */
export function useLiveJob(jobId: string) {
  const [status, setStatus] = useState<LiveStatus | null>(null);
  const [log, setLog] = useState<{ t: string; m: string }[]>([]);
  const lastStep = useRef<string | null>(null);

  useEffect(() => {
    if (!jobId) return;
    let alive = true;
    let timer: any;

    const stamp = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    const record = (s: LiveStatus) => {
      if (s.current_step && s.current_step !== lastStep.current) {
        lastStep.current = s.current_step;
        setLog((l) => [{ t: stamp(), m: s.current_step! }, ...l].slice(0, 60));
      }
    };

    const loadSupabase = async () => {
      try {
        const { data } = await supabase.from('seller_jobs').select('*').eq('job_id', jobId).maybeSingle();
        if (data && alive) {
          setStatus({
            status: data.status, progress: data.status === 'completed' ? 100 : 0,
            current_step: data.status === 'completed' ? 'Complete' : data.status,
            result: data.result_data || undefined, api_cost: data.result_data?.api_cost,
          });
        }
      } catch { /* noop */ }
    };

    const poll = async () => {
      try {
        const s = (await apiClient.checkJobStatus(jobId)) as unknown as LiveStatus;
        if (!alive) return;
        setStatus(s);
        record(s);
        if (s.status === 'processing' || s.status === 'pending') {
          timer = setTimeout(poll, 1500);
        }
      } catch {
        // not in memory (restarted / cross-device) — read the persisted copy
        await loadSupabase();
      }
    };

    poll();
    return () => { alive = false; clearTimeout(timer); };
  }, [jobId]);

  return { status, log };
}
