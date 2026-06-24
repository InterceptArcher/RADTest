'use client';

import { useState } from 'react';

/** A node in the platform webmap. */
interface MapNode {
  id: string;
  label: string;
  x: number;
  y: number;
  w: number;
  h: number;
  hub?: boolean;
  d: string;
}

// Ported verbatim from design-reference.html (DN array).
const DN: MapNode[] = [
  {
    id: 'platform',
    label: 'RAD Platform',
    x: 350,
    y: 160,
    w: 128,
    h: 40,
    hub: true,
    d: 'Your central hub for AI-powered company intelligence. The flag-gated v3.1 pipeline runs surgical contact discovery, a 28-specialist council, and exact-copy deck rendering.',
  },
  {
    id: 'start',
    label: 'Getting Started',
    x: 130,
    y: 60,
    w: 124,
    h: 34,
    d: 'Submit a company, domain and seller. The pipeline processes the request automatically and a deck is ready in roughly three minutes.',
  },
  {
    id: 'workflow',
    label: 'AI Workflow',
    x: 570,
    y: 60,
    w: 112,
    h: 34,
    d: 'A 28-specialist council plus surgical providers analyse financials, news, tech stack, competitors and stakeholders, synthesised into one intelligence report.',
  },
  {
    id: 'profiles',
    label: 'Company Profiles',
    x: 580,
    y: 260,
    w: 134,
    h: 34,
    d: 'Detailed overviews: revenue, headcount, IT spend, segments, geography, technologies, competitors and confidence-scored summaries.',
  },
  {
    id: 'sellers',
    label: 'Seller Mgmt',
    x: 120,
    y: 260,
    w: 112,
    h: 34,
    d: 'Create and manage sellers with monthly job limits. Track which rep requested each profile and monitor usage + spend per seller.',
  },
  {
    id: 'stakeholders',
    label: 'Stakeholders',
    x: 215,
    y: 160,
    w: 112,
    h: 34,
    d: 'Relevance-first decision-maker discovery with an email + phone + LinkedIn reachability floor of four contacts per deck.',
  },
  {
    id: 'pipeline',
    label: 'Data Pipeline',
    x: 485,
    y: 160,
    w: 114,
    h: 34,
    d: 'Live job tracking with per-stage progress, an audit log, and a running API-cost meter across every job.',
  },
];

// Ported verbatim from design-reference.html (DE array).
const DE: [string, string][] = [
  ['platform', 'start'],
  ['platform', 'workflow'],
  ['platform', 'profiles'],
  ['platform', 'sellers'],
  ['platform', 'stakeholders'],
  ['platform', 'pipeline'],
  ['start', 'stakeholders'],
  ['workflow', 'pipeline'],
  ['stakeholders', 'sellers'],
  ['pipeline', 'profiles'],
];

const byId = (id: string): MapNode | undefined => DN.find((n) => n.id === id);

const PLATFORM = byId('platform')!;

export default function DocsPage() {
  const [active, setActive] = useState<{ id: string; title: string; desc: string }>({
    id: PLATFORM.id,
    title: PLATFORM.label,
    desc: PLATFORM.d,
  });

  return (
    <section className="view" id="view-docs">
      <div className="docwrap">
        <div className="panel webmap">
          <div className="ph">
            <span className="eye"></span>
            <span className="k">Platform map</span>
            <h3>How RAD works</h3>
            <span className="n">click a node</span>
          </div>
          <div className="pb">
            <svg viewBox="0 0 700 320" id="map">
              <g id="edges">
                {DE.map(([a, b], i) => {
                  const A = byId(a);
                  const B = byId(b);
                  if (!A || !B) return null;
                  return (
                    <line
                      key={i}
                      x1={A.x}
                      y1={A.y}
                      x2={B.x}
                      y2={B.y}
                      className="map-edge"
                    />
                  );
                })}
              </g>
              <g id="nodes">
                {DN.map((n) => (
                  <g
                    key={n.id}
                    className={
                      'map-node' + (n.hub ? ' hub' : '') + (active.id === n.id ? ' on' : '')
                    }
                    style={{ cursor: 'pointer' }}
                    onClick={() => setActive({ id: n.id, title: n.label, desc: n.d })}
                  >
                    <rect
                      x={n.x - n.w / 2}
                      y={n.y - n.h / 2}
                      width={n.w}
                      height={n.h}
                      rx={10}
                    />
                    <text x={n.x} y={n.y + 4} textAnchor="middle">
                      {n.label}
                    </text>
                  </g>
                ))}
              </g>
            </svg>
          </div>
        </div>
        <div className="panel">
          <div className="ph">
            <span className="eye"></span>
            <span className="k">About</span>
            <h3 id="dt">{active.title}</h3>
          </div>
          <div className="pb">
            <p className="docdesc" id="dd">
              {active.desc}
            </p>
          </div>
        </div>
      </div>

      <div className="articles">
        <div className="art">
          <div className="at2">Guide</div>
          <h5>Getting started</h5>
          <p>
            Submit a company + domain and a seller. The pipeline runs automatically and a deck is
            ready in ~3 minutes.
          </p>
          <span className="more">Read →</span>
        </div>
        <div className="art">
          <div className="at2">How it works</div>
          <h5>The 9-stage pipeline</h5>
          <p>
            Orchestrator → discovery → enrich → intel → council → formatter → render. Watch it live
            in the job view.
          </p>
          <span className="more">Read →</span>
        </div>
        <div className="art">
          <div className="at2">People</div>
          <h5>Reading the stakeholder map</h5>
          <p>
            Relevance-first selection with an email + phone + LinkedIn reachability floor of 4 per
            deck.
          </p>
          <span className="more">Read →</span>
        </div>
        <div className="art">
          <div className="at2">Reference</div>
          <h5>API cost meter</h5>
          <p>
            Every job tallies Anthropic tokens + ZoomInfo + web-search calls into a per-job cost you
            can audit.
          </p>
          <span className="more">Read →</span>
        </div>
        <div className="art">
          <div className="at2">Admin</div>
          <h5>Managing sellers</h5>
          <p>
            Create sellers, set monthly job limits, and attribute every profile to the rep who
            requested it.
          </p>
          <span className="more">Read →</span>
        </div>
        <div className="art">
          <div className="at2">Reference</div>
          <h5>Canada-only mode</h5>
          <p>
            Restrict contact discovery to Canada — no US/global fallback — for region-sensitive
            accounts.
          </p>
          <span className="more">Read →</span>
        </div>
      </div>
    </section>
  );
}
