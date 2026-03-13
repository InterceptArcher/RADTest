'use client';

const NODES = [
  { x: 80, y: 50 }, { x: 220, y: 30 }, { x: 360, y: 70 }, { x: 500, y: 45 }, { x: 640, y: 65 }, { x: 760, y: 40 },
  { x: 50, y: 160 }, { x: 180, y: 190 }, { x: 330, y: 150 }, { x: 480, y: 175 }, { x: 610, y: 145 }, { x: 740, y: 170 },
  { x: 100, y: 290 }, { x: 250, y: 310 }, { x: 390, y: 270 }, { x: 540, y: 295 }, { x: 670, y: 275 }, { x: 770, y: 300 },
  { x: 60, y: 400 }, { x: 200, y: 430 }, { x: 350, y: 390 }, { x: 490, y: 415 }, { x: 630, y: 395 }, { x: 750, y: 420 },
  { x: 120, y: 520 }, { x: 270, y: 550 }, { x: 410, y: 510 }, { x: 560, y: 540 }, { x: 690, y: 515 },
];

const EDGES: [number, number][] = [
  [0,1], [1,2], [2,3], [3,4], [4,5],
  [6,7], [7,8], [8,9], [9,10], [10,11],
  [12,13], [13,14], [14,15], [15,16], [16,17],
  [18,19], [19,20], [20,21], [21,22], [22,23],
  [24,25], [25,26], [26,27], [27,28],
  [0,6], [1,7], [2,8], [3,9], [4,10], [5,11],
  [6,12], [7,13], [8,14], [9,15], [10,16], [11,17],
  [12,18], [13,19], [14,20], [15,21], [16,22], [17,23],
  [18,24], [19,25], [20,26], [21,27], [22,28],
  [0,7], [2,9], [4,11],
  [7,14], [9,16],
  [13,20], [15,22],
  [19,26], [21,28],
];

interface Props {
  className?: string;
  opacity?: number;
}

export default function NetworkBackground({ className = '', opacity = 0.05 }: Props) {
  return (
    <svg
      viewBox="0 0 800 600"
      preserveAspectRatio="xMidYMid slice"
      className={className}
      style={{ opacity }}
      aria-hidden="true"
    >
      <style>{`
        .nb-edge {
          stroke-dasharray: 6 6;
          animation: nbFlow 4s linear infinite;
        }
        .nb-node {
          animation: nbPulse 5s ease-in-out infinite;
        }
        @keyframes nbFlow {
          to { stroke-dashoffset: -12; }
        }
        @keyframes nbPulse {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 1; }
        }
      `}</style>

      {EDGES.map(([a, b], i) => (
        <line
          key={`e${i}`}
          x1={NODES[a].x}
          y1={NODES[a].y}
          x2={NODES[b].x}
          y2={NODES[b].y}
          stroke="currentColor"
          strokeWidth="0.8"
          className="nb-edge"
          style={{ animationDelay: `${(i * 0.15) % 4}s` }}
        />
      ))}

      {NODES.map((node, i) => (
        <circle
          key={`n${i}`}
          cx={node.x}
          cy={node.y}
          r="3"
          fill="currentColor"
          className="nb-node"
          style={{ animationDelay: `${(i * 0.3) % 5}s` }}
        />
      ))}
    </svg>
  );
}
