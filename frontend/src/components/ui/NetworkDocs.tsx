'use client';

import { useState } from 'react';

interface DocNode {
  id: string;
  label: string;
  cx: number;
  cy: number;
  w: number;
  h: number;
  description: string;
}

const NODES: DocNode[] = [
  { id: 'platform', label: 'RAD Platform', cx: 350, cy: 150, w: 130, h: 42, description: 'Your central hub for generating AI-powered company intelligence profiles. Powered by 20 specialized AI agents working in parallel to deliver comprehensive business insights.' },
  { id: 'start', label: 'Getting Started', cx: 120, cy: 55, w: 128, h: 34, description: 'Submit a company domain and salesperson email to generate a comprehensive intelligence profile. The AI council processes your request through 20 specialists automatically.' },
  { id: 'workflow', label: 'AI Workflow', cx: 580, cy: 55, w: 112, h: 34, description: '20 AI agents analyze company data in parallel — covering financials, news, tech stack, competitors, stakeholders, and more. Results are synthesized into a unified intelligence report.' },
  { id: 'profiles', label: 'Company Profiles', cx: 590, cy: 245, w: 138, h: 34, description: 'View detailed company overviews including revenue estimates, employee count, industry analysis, competitive landscape, and AI-generated executive summaries with confidence scores.' },
  { id: 'sellers', label: 'Seller Mgmt', cx: 110, cy: 245, w: 112, h: 34, description: 'Create and manage sellers with monthly bandwidth limits of 40 jobs. Track which salesperson requested each profile and monitor usage analytics per seller.' },
  { id: 'stakeholders', label: 'Stakeholders', cx: 210, cy: 150, w: 112, h: 34, description: 'Discover key decision-makers, their roles, and organizational hierarchy. Access contact information and LinkedIn profiles for targeted outreach strategies.' },
  { id: 'pipeline', label: 'Data Pipeline', cx: 490, cy: 150, w: 118, h: 34, description: 'Real-time job tracking with live progress updates. Monitor pending, processing, completed, and failed jobs across all sellers with detailed status information.' },
];

const EDGES: [string, string][] = [
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

export default function NetworkDocs() {
  const [activeId, setActiveId] = useState<string | null>(null);

  const getNode = (id: string) => NODES.find(n => n.id === id)!;
  const active = activeId ? getNode(activeId) : null;

  return (
    <div className="card overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-100">
        <h2 className="text-base font-semibold text-[#282727]">Platform Documentation</h2>
        <p className="text-sm text-[#939393] mt-0.5">Click a node to learn about each component.</p>
      </div>

      <div className="p-6">
        <svg viewBox="0 0 700 300" className="w-full" style={{ height: 280 }}>
          <defs>
            <style>{`
              .doc-edge {
                stroke-dasharray: 8 4;
                animation: docFlow 3s linear infinite;
              }
              @keyframes docFlow {
                to { stroke-dashoffset: -12; }
              }
            `}</style>
          </defs>

          {/* Edges */}
          {EDGES.map(([aId, bId], i) => {
            const a = getNode(aId);
            const b = getNode(bId);
            const isHighlighted = activeId === aId || activeId === bId;
            return (
              <line
                key={i}
                x1={a.cx} y1={a.cy} x2={b.cx} y2={b.cy}
                stroke={isHighlighted ? '#E02B23' : '#d1d5db'}
                strokeWidth={isHighlighted ? 2 : 1}
                className="doc-edge"
                style={{ animationDelay: `${i * 0.2}s`, transition: 'stroke 0.3s, stroke-width 0.3s' }}
              />
            );
          })}

          {/* Nodes */}
          {NODES.map((node) => {
            const isActive = activeId === node.id;
            const isCenter = node.id === 'platform';

            return (
              <g
                key={node.id}
                onClick={() => setActiveId(isActive ? null : node.id)}
                className="cursor-pointer"
              >
                {/* Glow for active */}
                {isActive && (
                  <rect
                    x={node.cx - node.w / 2 - 4}
                    y={node.cy - node.h / 2 - 4}
                    width={node.w + 8}
                    height={node.h + 8}
                    rx={node.h / 2 + 4}
                    fill="none"
                    stroke="#E02B23"
                    strokeWidth="1.5"
                    opacity="0.3"
                  >
                    <animate attributeName="opacity" values="0.3;0.1;0.3" dur="2s" repeatCount="indefinite" />
                  </rect>
                )}

                {/* Pill shape */}
                <rect
                  x={node.cx - node.w / 2}
                  y={node.cy - node.h / 2}
                  width={node.w}
                  height={node.h}
                  rx={node.h / 2}
                  fill={isActive ? '#E02B23' : isCenter ? '#282727' : '#ffffff'}
                  stroke={isActive ? '#E02B23' : isCenter ? '#282727' : '#d1d5db'}
                  strokeWidth={isCenter ? 0 : 1.5}
                  style={{ transition: 'fill 0.3s, stroke 0.3s' }}
                />

                {/* Label */}
                <text
                  x={node.cx}
                  y={node.cy}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fill={isActive || isCenter ? '#ffffff' : '#282727'}
                  fontSize={isCenter ? 13 : 11}
                  fontWeight={isCenter ? 700 : 600}
                  fontFamily="Inter, system-ui, sans-serif"
                  className="pointer-events-none select-none"
                  style={{ transition: 'fill 0.3s' }}
                >
                  {node.label}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Description panel */}
        <div
          className="overflow-hidden transition-all duration-300"
          style={{ maxHeight: active ? 200 : 0, opacity: active ? 1 : 0 }}
        >
          {active && (
            <div className="bg-slate-50 rounded-lg p-4 border border-slate-200 mt-4">
              <h3 className="text-sm font-semibold text-[#282727] mb-1">{active.label}</h3>
              <p className="text-sm text-[#939393] leading-relaxed">{active.description}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
