/**
 * ProcessFlowVisualization component for visualizing process flow.
 * Feature 021: Visualize Process to Output Flow
 */

'use client';

import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import type { ProcessFlow, ProcessFlowNode, ProcessFlowEdge } from '@/types';

interface ProcessFlowVisualizationProps {
  flow: ProcessFlow;
}

/**
 * Get node type icon.
 */
const getNodeIcon = (type: ProcessFlowNode['type']): string => {
  const icons: Record<ProcessFlowNode['type'], string> = {
    start: '▶',
    process: '⚙',
    decision: '◇',
    api: '🔗',
    llm: '🤖',
    end: '⏹',
  };
  return icons[type] || '●';
};

/**
 * Get node type class.
 */
const getNodeTypeClass = (type: ProcessFlowNode['type']): string => {
  const classes: Record<ProcessFlowNode['type'], string> = {
    start: 'border-green-500 bg-green-50',
    process: 'border-blue-500 bg-blue-50',
    decision: 'border-yellow-500 bg-yellow-50',
    api: 'border-purple-500 bg-purple-50',
    llm: 'border-indigo-500 bg-indigo-50',
    end: 'border-gray-500 bg-gray-50',
  };
  return `node-type-${type} ${classes[type] || 'border-gray-300 bg-gray-50'}`;
};

/**
 * Get node status class.
 */
const getNodeStatusClass = (status: ProcessFlowNode['status']): string => {
  const classes: Record<ProcessFlowNode['status'], string> = {
    pending: 'opacity-50',
    in_progress: 'ring-2 ring-blue-400 ring-offset-2',
    completed: 'opacity-100',
    failed: 'ring-2 ring-red-400 ring-offset-2',
  };
  return `node-${status} ${classes[status] || ''}`;
};

/**
 * Format duration for display.
 */
const formatDuration = (ms?: number): string => {
  if (!ms) return '';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
};

/**
 * Legend component for node types.
 */
const Legend = () => {
  const nodeTypes: Array<{ type: ProcessFlowNode['type']; label: string }> = [
    { type: 'start', label: 'Start' },
    { type: 'api', label: 'API Call' },
    { type: 'llm', label: 'LLM Process' },
    { type: 'decision', label: 'Decision' },
    { type: 'process', label: 'Process' },
    { type: 'end', label: 'End' },
  ];

  return (
    <div className="mt-4 p-3 bg-gray-50 rounded-md">
      <h4 className="text-xs font-medium text-gray-500 uppercase mb-2">
        Legend
      </h4>
      <div className="flex flex-wrap gap-3">
        {nodeTypes.map(({ type, label }) => (
          <div key={type} className="flex items-center gap-1.5">
            <span
              className={`w-6 h-6 flex items-center justify-center text-xs border-2 rounded ${getNodeTypeClass(type)}`}
            >
              {getNodeIcon(type)}
            </span>
            <span className="text-xs text-gray-600">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

/**
 * ProcessFlowVisualization displays a flowchart/timeline of the process.
 */
export default function ProcessFlowVisualization({
  flow,
}: ProcessFlowVisualizationProps) {
  const [zoom, setZoom] = useState(1);
  const [selectedNode, setSelectedNode] = useState<ProcessFlowNode | null>(
    null
  );
  const [focusedNodeIndex, setFocusedNodeIndex] = useState<number>(-1);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleZoomIn = useCallback(() => {
    setZoom((prev) => Math.min(prev + 0.1, 2));
  }, []);

  const handleZoomOut = useCallback(() => {
    setZoom((prev) => Math.max(prev - 0.1, 0.5));
  }, []);

  const handleZoomReset = useCallback(() => {
    setZoom(1);
  }, []);

  const handleNodeClick = useCallback((node: ProcessFlowNode) => {
    setSelectedNode((prev) => (prev?.id === node.id ? null : node));
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (flow.nodes.length === 0) return;

      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        e.preventDefault();
        setFocusedNodeIndex((prev) =>
          prev < flow.nodes.length - 1 ? prev + 1 : 0
        );
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        e.preventDefault();
        setFocusedNodeIndex((prev) =>
          prev > 0 ? prev - 1 : flow.nodes.length - 1
        );
      } else if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        if (focusedNodeIndex >= 0 && focusedNodeIndex < flow.nodes.length) {
          handleNodeClick(flow.nodes[focusedNodeIndex]);
        }
      }
    },
    [flow.nodes, focusedNodeIndex, handleNodeClick]
  );

  // Focus management
  useEffect(() => {
    if (focusedNodeIndex >= 0 && containerRef.current) {
      const nodeElement = containerRef.current.querySelector(
        `[data-node-index="${focusedNodeIndex}"]`
      ) as HTMLElement;
      nodeElement?.focus();
    }
  }, [focusedNodeIndex]);

  // Organize nodes into rows for visualization
  const nodeRows = useMemo(() => {
    if (flow.nodes.length === 0) return [];

    // Simple row-based layout
    const rows: ProcessFlowNode[][] = [];
    let currentRow: ProcessFlowNode[] = [];

    flow.nodes.forEach((node, index) => {
      currentRow.push(node);
      if (currentRow.length >= 3 || index === flow.nodes.length - 1) {
        rows.push([...currentRow]);
        currentRow = [];
      }
    });

    return rows;
  }, [flow.nodes]);

  // Find active node
  const activeNode = useMemo(
    () => flow.nodes.find((n) => n.status === 'in_progress'),
    [flow.nodes]
  );

  if (flow.nodes.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Process Flow</h2>
        <div className="text-center py-8 text-gray-500">
          <p>No process flow data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Process Flow</h2>

        {/* Zoom Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleZoomOut}
            className="p-2 text-gray-600 bg-gray-100 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
            aria-label="Zoom out"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
            </svg>
          </button>
          <button
            onClick={handleZoomReset}
            className="px-3 py-1.5 text-sm text-gray-600 bg-gray-100 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
            aria-label="Reset zoom"
          >
            Reset
          </button>
          <button
            onClick={handleZoomIn}
            className="p-2 text-gray-600 bg-gray-100 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
            aria-label="Zoom in"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          </button>
        </div>
      </div>

      {/* Flow Visualization */}
      <div
        ref={containerRef}
        data-testid="flow-visualization"
        data-zoom={zoom}
        className="flow-container responsive relative overflow-auto border border-gray-200 rounded-lg p-6 bg-gray-50"
        style={{ transform: `scale(${zoom})`, transformOrigin: 'top left' }}
        onKeyDown={handleKeyDown}
        role="img"
        aria-label="Process flow diagram"
        aria-describedby="flow-description"
      >
        <span id="flow-description" className="sr-only">
          Interactive process flow diagram showing {flow.nodes.length} steps
          from start to completion
        </span>

        {/* Nodes */}
        <div className="space-y-8">
          {nodeRows.map((row, rowIndex) => (
            <div
              key={rowIndex}
              className="flex items-center justify-center gap-8"
            >
              {row.map((node, nodeIndex) => {
                const globalIndex =
                  rowIndex * 3 + nodeIndex;
                const isActive = activeNode?.id === node.id;
                const isFocused = focusedNodeIndex === globalIndex;

                return (
                  <div key={node.id} className="flex items-center gap-4">
                    {/* Node */}
                    <button
                      data-testid={`node-${node.id}`}
                      data-node-index={globalIndex}
                      onClick={() => handleNodeClick(node)}
                      className={`
                        relative flex flex-col items-center justify-center
                        w-28 h-20 rounded-lg border-2 cursor-pointer
                        transition-all duration-200
                        focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2
                        ${getNodeTypeClass(node.type)}
                        ${getNodeStatusClass(node.status)}
                        ${isActive ? 'node-active animating' : ''}
                        ${isFocused ? 'ring-2 ring-primary-400' : ''}
                      `}
                      tabIndex={0}
                      role="button"
                      aria-label={`${node.label}, ${node.status}`}
                    >
                      <span className="text-lg mb-1">{getNodeIcon(node.type)}</span>
                      <span className="text-xs font-medium text-center px-1 truncate w-full">
                        {node.label}
                      </span>
                      {node.duration && (
                        <span className="absolute -bottom-5 text-xs text-gray-500">
                          {formatDuration(node.duration)}
                        </span>
                      )}
                      {isActive && (
                        <span className="absolute -top-1 -right-1 w-3 h-3 bg-blue-500 rounded-full animate-ping" />
                      )}
                    </button>

                    {/* Edge to next node (if not last in row) */}
                    {nodeIndex < row.length - 1 && (
                      <div
                        data-testid={`edge-${globalIndex}`}
                        className="flex items-center"
                      >
                        <div className="w-12 h-0.5 bg-gray-300" />
                        <svg
                          className="w-3 h-3 text-gray-400 -ml-1"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path
                            fillRule="evenodd"
                            d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z"
                            clipRule="evenodd"
                          />
                        </svg>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ))}

          {/* Vertical edges between rows */}
          {nodeRows.length > 1 &&
            nodeRows.slice(0, -1).map((_, rowIndex) => (
              <div
                key={`vertical-edge-${rowIndex}`}
                data-testid={`edge-vertical-${rowIndex}`}
                className="flex justify-center -mt-4 -mb-4"
              >
                <div className="w-0.5 h-8 bg-gray-300" />
              </div>
            ))}
        </div>

        {/* Edge labels */}
        {flow.edges
          .filter((e) => e.label)
          .map((edge) => (
            <span
              key={edge.id}
              data-testid={`edge-${edge.id}`}
              className="absolute text-xs text-gray-500 bg-white px-1 rounded"
            >
              {edge.label}
            </span>
          ))}
      </div>

      {/* Selected Node Details */}
      {selectedNode && (
        <div className="mt-4 p-4 bg-gray-100 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-medium text-gray-900">{selectedNode.label}</h3>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-gray-500 hover:text-gray-700"
              aria-label="Close details"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          {selectedNode.details && (
            <p className="text-sm text-gray-700 mb-2">{selectedNode.details}</p>
          )}
          {selectedNode.duration && (
            <p className="text-sm text-gray-500">
              Duration: {formatDuration(selectedNode.duration)}
            </p>
          )}
          <p className="text-sm text-gray-500 capitalize">
            Status: {selectedNode.status.replace('_', ' ')}
          </p>
        </div>
      )}

      {/* Fallback for non-JS */}
      <noscript>
        <div className="flow-fallback p-4 bg-yellow-50 border border-yellow-200 rounded-md mt-4">
          <p className="text-sm text-yellow-800">
            JavaScript is required to view the interactive process flow
            visualization.
          </p>
          <ul className="mt-2 text-sm text-yellow-700">
            {flow.nodes.map((node, index) => (
              <li key={node.id}>
                {index + 1}. {node.label} ({node.status})
              </li>
            ))}
          </ul>
        </div>
      </noscript>

      {/* Legend */}
      <Legend />
    </div>
  );
}
