/**
 * Canonical v3.1 pipeline stages for the live flowchart, and a mapping from the
 * backend's progress/current_step to which node is active. The backend emits
 * progress 10→100 with named steps; we bucket those into the 9 visible nodes.
 */
export interface Stage { label: string; icon: string; }

export const STAGES: Stage[] = [
  { label: 'Initialize', icon: 'M12 2v6m0 8v6M2 12h6m8 0h6' },
  { label: 'Orchestrator', icon: 'M4 6h16M4 12h10M4 18h7' },
  { label: 'Contact Discovery', icon: 'M21 21l-4.3-4.3M11 18a7 7 0 100-14 7 7 0 000 14z' },
  { label: 'Enrich & Validate', icon: 'M9 12l2 2 4-4M12 2l8 4v6c0 5-3.5 8-8 10-4.5-2-8-5-8-10V6z' },
  { label: 'Company Intel', icon: 'M3 12h4l3 8 4-16 3 8h4' },
  { label: 'LLM Council', icon: 'M12 3l8 4.5v9L12 21l-8-4.5v-9zM12 3v18' },
  { label: 'Formatter', icon: 'M4 5h16M4 12h16M4 19h10' },
  { label: 'Deck Render', icon: 'M3 4h18v12H3zM8 20h8M12 16v4' },
  { label: 'Complete', icon: 'M5 13l4 4L19 7' },
];

/** Index of the currently-active node from backend progress + status. */
export function activeStage(progress: number, status: string): number {
  if (status === 'completed') return 8;
  const p = progress || 0;
  if (p >= 90) return 7;
  if (p >= 80) return 6;
  if (p >= 60) return 5;
  if (p >= 55) return 4;
  if (p >= 46) return 3;
  if (p >= 20) return 2;
  if (p >= 15) return 1;
  return 0;
}

export type NodeState = 'done' | 'act' | 'fail' | '';

/** Per-node visual state for the flowchart. */
export function nodeStates(progress: number, status: string): NodeState[] {
  const active = activeStage(progress, status);
  const failed = status === 'failed';
  return STAGES.map((_, i) => {
    if (status === 'completed') return 'done';
    if (failed) return i < active ? 'done' : i === active ? 'fail' : '';
    if (i < active) return 'done';
    if (i === active) return 'act';
    return '';
  });
}
