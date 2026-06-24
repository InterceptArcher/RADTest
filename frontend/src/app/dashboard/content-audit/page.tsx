'use client';

import { useEffect, useMemo, useState } from 'react';
import { apiClient } from '@/lib/api';

interface Item {
  asset_name?: string; name?: string; title?: string;
  asset_summary?: string; industry?: string; consideration?: string;
  format?: string; audience?: string; marketing_or_sales?: string;
  service_solution?: string; sp_link?: string; link?: string; url?: string;
  [k: string]: unknown;
}

const name = (i: Item) => i.asset_name || i.name || i.title || 'Untitled asset';
const link = (i: Item) => i.sp_link || i.link || i.url || '';
const summary = (i: Item) => (i.asset_summary || '').toString();
const emoji = (i: Item) => {
  const f = (i.format || '').toLowerCase();
  if (f.includes('thought')) return '💡';
  if (f.includes('prescriptive')) return '🧭';
  if (f.includes('product')) return '🧩';
  return '📄';
};
const tags = (i: Item) => [i.consideration, i.format, i.audience,
  i.industry && i.industry !== 'Industry agnostic' ? i.industry : '']
  .filter((t): t is string => typeof t === 'string' && t.trim().length > 0);

const FUNNEL = ['Awareness', 'Consideration', 'Decision'];

export default function ContentAuditPage() {
  const [items, setItems] = useState<Item[]>([]);
  const [fetched, setFetched] = useState(false);
  const [filter, setFilter] = useState('All');

  useEffect(() => {
    apiClient.getContentAudit()
      .then((d) => setItems(Array.isArray(d) ? (d as Item[]) : []))
      .finally(() => setFetched(true));
  }, []);

  const counts = useMemo(() => {
    const c: Record<string, number> = { All: items.length };
    FUNNEL.forEach((f) => { c[f] = items.filter((i) => (i.consideration || '') === f).length; });
    return c;
  }, [items]);

  const shown = filter === 'All' ? items : items.filter((i) => (i.consideration || '') === filter);
  const loading = !fetched && items.length === 0;

  return (
    <>
      <div className="filters">
        {['All', ...FUNNEL].map((f) => (
          <span key={f} className={'f' + (filter === f ? ' on' : '')} onClick={() => setFilter(f)}>
            {f} · {counts[f] ?? 0}
          </span>
        ))}
        <span className="f" style={{ marginLeft: 'auto' }}>HP Canada DAM · {items.length} assets</span>
      </div>

      {loading ? (
        <div className="await"><span className="d" /> loading content audit…</div>
      ) : shown.length === 0 ? (
        <div className="await">No assets match this filter.</div>
      ) : (
        <div className="ca-grid">
          {shown.map((it, idx) => {
            const href = link(it);
            return (
              <div className="asset" key={idx}>
                <div className="thumb">{emoji(it)}</div>
                <div className="an">{name(it)}</div>
                {summary(it) && (
                  <div style={{ fontSize: 11.5, color: 'var(--muted)', lineHeight: 1.5,
                    display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                    {summary(it)}
                  </div>
                )}
                <div className="tags">{tags(it).map((t, i) => <span className="tag" key={i}>{t}</span>)}</div>
                {href
                  ? <a className="lk" href={href} target="_blank" rel="noopener noreferrer">↗ Open in DAM</a>
                  : <span className="lk" style={{ opacity: .5 }}>no DAM link</span>}
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}
