'use client';

/**
 * Notification state for the bell (alerts) and the inbox "X new" pill.
 *
 * Two independent per-device sets, persisted to localStorage (NOT Supabase —
 * "seen"/"viewed" is intentionally per-device, so dismissing an alert on your
 * laptop doesn't wipe it on a teammate's screen):
 *   - dismissed: bell alerts the user has hovered/flagged as seen.
 *   - viewed:    finished jobs whose deck the user has opened from the inbox.
 *
 * The pure helpers (toNotifications / unseenCount) carry the finished-job logic
 * and are unit-tested in isolation.
 */
import {
  createContext, useContext, useState, useEffect, useCallback, useMemo, ReactNode,
} from 'react';
import type { JobWithMetadata } from '@/types';

const DISMISSED_KEY = 'radar_dismissed_alerts';
const VIEWED_KEY = 'radar_viewed_jobs';

export type NotifKind = 'completed' | 'failed';

export interface JobNotification {
  jobId: string;
  companyName: string;
  kind: NotifKind;
  /** completedAt when present, else createdAt — used for ordering. */
  at: string;
}

/**
 * Reduce jobs to finished-job notifications (completed + failed), newest first.
 */
export function toNotifications(jobs: JobWithMetadata[]): JobNotification[] {
  return jobs
    .filter((j) => j.status === 'completed' || j.status === 'failed')
    .map((j) => ({
      jobId: j.jobId,
      companyName: j.companyName,
      kind: j.status as NotifKind,
      at: j.completedAt || j.createdAt,
    }))
    .sort((a, b) => new Date(b.at).getTime() - new Date(a.at).getTime());
}

/**
 * How many finished jobs are NOT in the provided seen/viewed collection.
 */
export function unseenCount(
  jobs: JobWithMetadata[],
  seen: Set<string> | string[],
): number {
  const set = Array.isArray(seen) ? new Set(seen) : seen;
  return toNotifications(jobs).filter((n) => !set.has(n.jobId)).length;
}

interface NotificationsContextType {
  dismissed: Set<string>;
  viewed: Set<string>;
  dismissAlert: (jobId: string) => void;
  markViewed: (jobId: string) => void;
  isDismissed: (jobId: string) => boolean;
  isViewed: (jobId: string) => boolean;
}

const NotificationsContext = createContext<NotificationsContextType | undefined>(undefined);

function loadSet(key: string): string[] {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const [dismissed, setDismissed] = useState<string[]>([]);
  const [viewed, setViewed] = useState<string[]>([]);

  // Hydrate from localStorage on mount (client-only).
  useEffect(() => {
    setDismissed(loadSet(DISMISSED_KEY));
    setViewed(loadSet(VIEWED_KEY));
  }, []);

  useEffect(() => {
    try { localStorage.setItem(DISMISSED_KEY, JSON.stringify(dismissed)); } catch { /* ignore */ }
  }, [dismissed]);

  useEffect(() => {
    try { localStorage.setItem(VIEWED_KEY, JSON.stringify(viewed)); } catch { /* ignore */ }
  }, [viewed]);

  const dismissAlert = useCallback((jobId: string) => {
    setDismissed((prev) => (prev.includes(jobId) ? prev : [...prev, jobId]));
  }, []);

  const markViewed = useCallback((jobId: string) => {
    setViewed((prev) => (prev.includes(jobId) ? prev : [...prev, jobId]));
  }, []);

  const dismissedSet = useMemo(() => new Set(dismissed), [dismissed]);
  const viewedSet = useMemo(() => new Set(viewed), [viewed]);

  const value = useMemo<NotificationsContextType>(() => ({
    dismissed: dismissedSet,
    viewed: viewedSet,
    dismissAlert,
    markViewed,
    isDismissed: (jobId: string) => dismissedSet.has(jobId),
    isViewed: (jobId: string) => viewedSet.has(jobId),
  }), [dismissedSet, viewedSet, dismissAlert, markViewed]);

  return (
    <NotificationsContext.Provider value={value}>
      {children}
    </NotificationsContext.Provider>
  );
}

export function useNotifications() {
  const ctx = useContext(NotificationsContext);
  if (ctx === undefined) {
    throw new Error('useNotifications must be used within a NotificationsProvider');
  }
  return ctx;
}
