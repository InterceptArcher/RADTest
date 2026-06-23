/**
 * ConfidenceBadge — v3.1. Maps a 0–1 data_quality_score to a High/Medium/Low pill.
 * Provisional thresholds (tunable, must match backend bi_resolver.quality_band):
 *   High >= 0.75, Medium 0.4–0.75, Low < 0.4.
 */
'use client';

interface ConfidenceBadgeProps {
  score?: number;
}

export default function ConfidenceBadge({ score }: ConfidenceBadgeProps) {
  if (score === undefined || score === null) return null;

  const band = score >= 0.75 ? 'High' : score >= 0.4 ? 'Medium' : 'Low';
  const styles: Record<string, string> = {
    High: 'bg-green-100 text-green-800 border-green-300',
    Medium: 'bg-amber-100 text-amber-800 border-amber-300',
    Low: 'bg-red-100 text-red-800 border-red-300',
  };

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${styles[band]}`}
      title={`Data quality score: ${(score * 100).toFixed(0)}%`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {band} confidence · {(score * 100).toFixed(0)}%
    </span>
  );
}
