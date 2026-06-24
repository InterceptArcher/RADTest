'use client';

import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api';

/**
 * Content Audit V2 (DAM) asset — shape is intentionally loose because the
 * backend payload varies; every field is read defensively below.
 */
interface ContentAuditItem {
  asset_name?: string;
  name?: string;
  title?: string;
  industry?: string;
  funnel_stage?: string;
  stage?: string;
  type?: string;
  sp_link?: string;
  link?: string;
  url?: string;
  [key: string]: unknown;
}

function assetName(item: ContentAuditItem): string {
  return item.asset_name || item.name || item.title || 'Untitled asset';
}

function assetTags(item: ContentAuditItem): string[] {
  return [item.industry, item.funnel_stage, item.stage, item.type].filter(
    (t): t is string => typeof t === 'string' && t.trim().length > 0
  );
}

function assetLink(item: ContentAuditItem): string | undefined {
  return item.sp_link || item.link || item.url || undefined;
}

export default function ContentAuditPage() {
  const [items, setItems] = useState<ContentAuditItem[]>([]);
  const [fetched, setFetched] = useState(false);

  useEffect(() => {
    apiClient
      .getContentAudit()
      .then((data) => setItems(Array.isArray(data) ? (data as ContentAuditItem[]) : []))
      .finally(() => setFetched(true));
  }, []);

  const loading = items.length === 0 && !fetched;

  return (
    <section className="view" id="view-content">
      <div className="filters">
        <span className="f on">All · {items.length}</span>
        <span className="f">Awareness</span>
        <span className="f">Consideration</span>
        <span className="f">Decision</span>
        <span className="f">Technology</span>
        <span className="f">Insurance</span>
      </div>

      {loading ? (
        <div className="await">loading content audit…</div>
      ) : items.length === 0 ? (
        <div className="await">No content audit assets found yet.</div>
      ) : (
        <div className="ca-grid">
          {items.map((item, idx) => {
            const link = assetLink(item);
            return (
              <div className="asset" key={idx}>
                <div className="thumb">📄</div>
                <div className="an">{assetName(item)}</div>
                <div className="tags">
                  {assetTags(item).map((tag, i) => (
                    <span className="tag" key={i}>
                      {tag}
                    </span>
                  ))}
                </div>
                {link ? (
                  <a className="lk" href={link} target="_blank" rel="noopener noreferrer">
                    ↗ Open in DAM
                  </a>
                ) : (
                  <a className="lk">↗ Open in DAM</a>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
