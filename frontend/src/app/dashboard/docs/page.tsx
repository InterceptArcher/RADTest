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

interface Article { tag: string; title: string; blurb: string; body: { h?: string; p: string[] }[]; }

const ARTICLES: Article[] = [
  {
    tag: 'Guide', title: 'Getting started',
    blurb: 'Launch a profile and watch it build in ~3 minutes.',
    body: [
      { h: 'Launch a profile', p: ['From Home, fill in the company name, domain, and (optionally) industry. Enter your email under "Requested by" and the rep\'s name under "Salesperson" — that name is printed on the deck and automatically becomes a seller. Flip "Canada-only contacts" if the account needs Canadian stakeholders only, then hit Launch profile.'] },
      { h: 'Watch it run live', p: ['You\'re taken straight to the Job View. A nine-node flowchart lights up stage by stage, the intelligence panels fill in as each section is validated, and the audit log and API cost meter update in real time.'] },
      { h: 'Get the deck', p: ['When the pipeline completes, the "Slideshow" button in the header activates — that\'s a ready-to-send HP .pptx. "Debug" opens the raw API responses behind every section for spot-checking.'] },
    ],
  },
  {
    tag: 'How it works', title: 'The 9-stage pipeline',
    blurb: 'Orchestrator → discovery → enrich → intel → council → render.',
    body: [
      { h: 'The stages', p: ['Initialize sets up the job. The Orchestrator decides which data sources to call. Contact Discovery runs a surgical, per-persona ZoomInfo search. Enrich & Validate fills email / phone / LinkedIn and fact-checks. Company Intel adds firmographics via web search. The LLM Council — 28 specialists — synthesizes opportunity themes and the recommended sales program. The Formatter authors the slide copy, and Deck Render produces the exact-copy .pptx.'] },
      { h: 'Reading the flowchart', p: ['Each stage is a node: a green check means done, a pulsing blue node is running now, and dim nodes are queued. The connector feeding the active node animates so you can see momentum. If a stage fails, its node turns red.'] },
    ],
  },
  {
    tag: 'People', title: 'Reading the stakeholder map',
    blurb: 'Relevance-first picks, with a reachability floor of four.',
    body: [
      { h: 'Relevance first', p: ['For each persona — CIO, CTO, CFO, COO, CISO, CPO — the pipeline picks the closest title match and then enriches it, rather than picking whoever happens to have the most data on hand. The right executive comes first.'] },
      { h: 'The reachability floor', p: ['Every deck aims for at least four contacts that each have an email, a phone, and a LinkedIn URL. If the most relevant exec can\'t be made reachable, a reachable alternate is swapped in so the rep always has people they can actually contact.'] },
      { h: 'The dossier', p: ['Click any person in the Stakeholder map to open their dossier on the right — title, a short bio, and their email / phone / LinkedIn. Missing channels are shown explicitly (for example, "no direct line on file").'] },
    ],
  },
  {
    tag: 'Reference', title: 'The API cost meter',
    blurb: 'A per-job USD estimate, broken down by service.',
    body: [
      { h: 'What\'s counted', p: ['Every job tallies LLM token usage (Anthropic for enrichment plus the OpenAI council), ZoomInfo API calls, and web searches into a single per-job dollar estimate. It shows live in the Job View header and Trace section, and as a column in the Jobs queue and the Home activity feed.'] },
      { h: 'How it\'s priced', p: ['Token-based costs are priced per model from each response\'s usage, so they\'re close to exact. ZoomInfo has no tokens to price on, so it\'s a per-call estimate — the meter shows the call count next to it so the basis is transparent. The per-call rate is easy to tune to your plan\'s credit price.'] },
    ],
  },
  {
    tag: 'Admin', title: 'Managing sellers',
    blurb: 'Sellers are created automatically from the salesperson name.',
    body: [
      { h: 'No manual setup', p: ['You don\'t create sellers by hand. When you type a Salesperson name on the intake form — the same name that prints on the deck — a seller is found or created automatically and the job is attributed to them.'] },
      { h: 'Monthly draws', p: ['The Sellers tab shows a single team-wide "draws this month" meter against a 40 / month guide. It\'s a visual indicator: it\'s allowed to run over 40 (it turns amber and shows how many over), and it resets at the start of each calendar month. Each seller card shows that seller\'s monthly draw count, total jobs, spend, and success rate.'] },
    ],
  },
  {
    tag: 'Reference', title: 'Canada-only mode',
    blurb: 'Restrict contact discovery to Canada.',
    body: [
      { h: 'When to use it', p: ['Toggle "Canada-only contacts" on the intake form for region-sensitive accounts. ZoomInfo discovery is then restricted to Canada with no US or global fallback, so every contact on the deck is Canadian.'] },
      { h: 'What you get', p: ['Canada-only decks are saved with a "_ca" suffix on the filename so they never overwrite the company\'s global deck. If ZoomInfo has few Canadian contacts for a large multinational, the deck may carry fewer than four reachable contacts — that\'s expected and honest, rather than padded with non-Canadian people.'] },
    ],
  },
];

export default function DocsPage() {
  const [active, setActive] = useState<{ id: string; title: string; desc: string }>({
    id: PLATFORM.id,
    title: PLATFORM.label,
    desc: PLATFORM.d,
  });
  const [openIdx, setOpenIdx] = useState<number | null>(null);

  return (
    <section id="view-docs">
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

      <div className="secthead" style={{ margin: '8px 2px 14px' }}>Guides · click to read</div>
      <div className="articles">
        {ARTICLES.map((a, i) => (
          <div className="art" key={i} onClick={() => setOpenIdx(i)} role="button" tabIndex={0}
            onKeyDown={(e) => { if (e.key === 'Enter') setOpenIdx(i); }}>
            <div className="at2">{a.tag}</div>
            <h5>{a.title}</h5>
            <p>{a.blurb}</p>
            <span className="more">Read →</span>
          </div>
        ))}
      </div>

      {openIdx !== null && (
        <div className="modal" onClick={() => setOpenIdx(null)}>
          <div className="modalcard" onClick={(e) => e.stopPropagation()}>
            <button className="mclose" onClick={() => setOpenIdx(null)} aria-label="Close">×</button>
            <div className="mtag">{ARTICLES[openIdx].tag}</div>
            <h2>{ARTICLES[openIdx].title}</h2>
            <div className="article-body">
              {ARTICLES[openIdx].body.map((s, j) => (
                <div key={j}>
                  {s.h && <h4>{s.h}</h4>}
                  {s.p.map((para, k) => <p key={k}>{para}</p>)}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
