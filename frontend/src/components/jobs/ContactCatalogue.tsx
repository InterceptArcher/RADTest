/**
 * ContactCatalogue — v3.1. Collapsible per-persona view of examined contacts
 * across the six personas (CIO/CTO/CFO/COO/CISO/CPO). Selected contact(s) shown
 * on top; rejected ones below with their reason annotations (`marks`). Renders
 * nothing if the job has no v3.1 catalogue, so it is safe on legacy jobs.
 */
'use client';

import { useState } from 'react';
import type { ContactCatalogue as Catalogue, CatalogueContact } from '@/types';

const PERSONA_ORDER = ['CIO', 'CTO', 'CFO', 'COO', 'CISO', 'CPO'];

const PERSONA_LABEL: Record<string, string> = {
  CIO: 'Chief Information Officer',
  CTO: 'Chief Technology Officer',
  CFO: 'Chief Financial Officer',
  COO: 'Chief Operating Officer',
  CISO: 'Chief Information Security Officer',
  CPO: 'Chief Product Officer',
};

function ContactRow({ c }: { c: CatalogueContact }) {
  if (c.is_sentinel) {
    return (
      <div className="rounded border border-dashed border-slate-300 px-3 py-2 text-sm text-slate-500">
        No contact found for this persona
      </div>
    );
  }
  return (
    <div className="rounded border border-slate-200 px-3 py-2 text-sm">
      <div className="flex items-center justify-between">
        <div className="font-semibold text-slate-900">{c.name}</div>
        {c.source && (
          <span className="text-xs uppercase tracking-wide text-slate-400">{c.source}</span>
        )}
      </div>
      {c.title && <div className="text-slate-600">{c.title}</div>}
      <div className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-slate-500">
        {c.email && <span>{c.email}</span>}
        {c.start_date && <span>Start: {c.start_date}</span>}
        {c.linkedin_url && (
          <a href={c.linkedin_url} target="_blank" rel="noopener noreferrer"
             className="text-[#024AD8] hover:underline">LinkedIn</a>
        )}
      </div>
      {c.marks && c.marks.length > 0 && (
        <div className="mt-1 flex flex-wrap gap-1">
          {c.marks.map((m, i) => (
            <span key={i} className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500">{m}</span>
          ))}
        </div>
      )}
    </div>
  );
}

interface ContactCatalogueProps {
  catalogue?: Catalogue;
  selected?: Catalogue;
}

export default function ContactCatalogue({ catalogue, selected }: ContactCatalogueProps) {
  const [open, setOpen] = useState<Record<string, boolean>>({});
  if (!catalogue || Object.keys(catalogue).length === 0) return null;

  const personas = PERSONA_ORDER.filter((p) => (catalogue[p]?.length ?? 0) > 0 || (selected?.[p]?.length ?? 0) > 0);
  if (personas.length === 0) return null;

  return (
    <div className="card p-4 mb-6">
      <h3 className="mb-3 text-sm font-semibold text-slate-900">Contact Catalogue (by persona)</h3>
      <div className="space-y-3">
        {personas.map((persona) => {
          const sel = selected?.[persona] ?? [];
          const examined = catalogue[persona] ?? [];
          const selectedKeys = new Set(sel.map((s) => s.linkedin_url || s.name));
          const rejected = examined.filter((c) => !selectedKeys.has(c.linkedin_url || c.name));
          const isOpen = open[persona] ?? false;
          return (
            <div key={persona} className="rounded-lg border border-slate-200 p-3">
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-semibold text-slate-900">{persona}</span>
                  <span className="ml-2 text-xs text-slate-400">{PERSONA_LABEL[persona]}</span>
                </div>
                {rejected.length > 0 && (
                  <button onClick={() => setOpen({ ...open, [persona]: !isOpen })}
                          className="text-xs text-slate-500 hover:text-slate-800">
                    {isOpen ? 'Hide' : `Show ${rejected.length} examined`}
                  </button>
                )}
              </div>
              <div className="mt-2 space-y-1.5">
                {sel.length > 0
                  ? sel.map((c, i) => <ContactRow key={`s${i}`} c={c} />)
                  : <div className="text-xs italic text-slate-400">Not represented on the deck</div>}
              </div>
              {isOpen && rejected.length > 0 && (
                <div className="mt-2 space-y-1.5 border-t border-slate-100 pt-2">
                  <div className="text-[11px] uppercase tracking-wide text-slate-400">Examined / not selected</div>
                  {rejected.map((c, i) => <ContactRow key={`r${i}`} c={c} />)}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
