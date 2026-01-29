/**
 * Tests for ProcessFlowVisualization component.
 * Feature 021: Visualize Process to Output Flow
 * Following TDD - tests written first.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ProcessFlowVisualization from '../ProcessFlowVisualization';
import type { ProcessFlow } from '@/types';

describe('ProcessFlowVisualization', () => {
  const mockProcessFlow: ProcessFlow = {
    nodes: [
      {
        id: 'node-start',
        label: 'Request Received',
        type: 'start',
        status: 'completed',
        details: 'Company profile request initiated',
        duration: 100,
      },
      {
        id: 'node-apollo',
        label: 'Apollo.io API',
        type: 'api',
        status: 'completed',
        details: 'Fetched company data from Apollo.io',
        duration: 2500,
      },
      {
        id: 'node-pdl',
        label: 'PeopleDataLabs API',
        type: 'api',
        status: 'completed',
        details: 'Fetched company data from PeopleDataLabs',
        duration: 1800,
      },
      {
        id: 'node-validate',
        label: 'LLM Validation',
        type: 'llm',
        status: 'completed',
        details: 'Data validated by LLM agents',
        duration: 5000,
      },
      {
        id: 'node-decision',
        label: 'Data Discrepancy?',
        type: 'decision',
        status: 'completed',
        details: 'Checking for data conflicts',
      },
      {
        id: 'node-resolve',
        label: 'LLM Council',
        type: 'llm',
        status: 'in_progress',
        details: 'Resolving conflicts with LLM council',
        duration: 3000,
      },
      {
        id: 'node-gamma',
        label: 'Gamma API',
        type: 'api',
        status: 'pending',
        details: 'Generate slideshow',
      },
      {
        id: 'node-end',
        label: 'Complete',
        type: 'end',
        status: 'pending',
      },
    ],
    edges: [
      { id: 'edge-1', source: 'node-start', target: 'node-apollo' },
      { id: 'edge-2', source: 'node-start', target: 'node-pdl' },
      { id: 'edge-3', source: 'node-apollo', target: 'node-validate' },
      { id: 'edge-4', source: 'node-pdl', target: 'node-validate' },
      { id: 'edge-5', source: 'node-validate', target: 'node-decision' },
      { id: 'edge-6', source: 'node-decision', target: 'node-resolve', label: 'Yes' },
      { id: 'edge-7', source: 'node-decision', target: 'node-gamma', label: 'No' },
      { id: 'edge-8', source: 'node-resolve', target: 'node-gamma' },
      { id: 'edge-9', source: 'node-gamma', target: 'node-end' },
    ],
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render process flow visualization with title', () => {
    render(<ProcessFlowVisualization flow={mockProcessFlow} />);

    expect(screen.getByText(/process flow/i)).toBeInTheDocument();
  });

  it('should display all flow nodes', () => {
    render(<ProcessFlowVisualization flow={mockProcessFlow} />);

    expect(screen.getByText('Request Received')).toBeInTheDocument();
    expect(screen.getByText('Apollo.io API')).toBeInTheDocument();
    expect(screen.getByText('PeopleDataLabs API')).toBeInTheDocument();
    expect(screen.getByText('LLM Validation')).toBeInTheDocument();
    expect(screen.getByText('Data Discrepancy?')).toBeInTheDocument();
    expect(screen.getByText('LLM Council')).toBeInTheDocument();
    expect(screen.getByText('Gamma API')).toBeInTheDocument();
    expect(screen.getByText('Complete')).toBeInTheDocument();
  });

  it('should display node status with appropriate styling', () => {
    render(<ProcessFlowVisualization flow={mockProcessFlow} />);

    const startNode = screen.getByTestId('node-node-start');
    const inProgressNode = screen.getByTestId('node-node-resolve');
    const pendingNode = screen.getByTestId('node-node-end');

    expect(startNode).toHaveClass('node-completed');
    expect(inProgressNode).toHaveClass('node-in_progress');
    expect(pendingNode).toHaveClass('node-pending');
  });

  it('should display different node types with appropriate icons', () => {
    render(<ProcessFlowVisualization flow={mockProcessFlow} />);

    // Check for type-specific styling/icons
    const apiNode = screen.getByTestId('node-node-apollo');
    const llmNode = screen.getByTestId('node-node-validate');
    const decisionNode = screen.getByTestId('node-node-decision');

    expect(apiNode).toHaveClass('node-type-api');
    expect(llmNode).toHaveClass('node-type-llm');
    expect(decisionNode).toHaveClass('node-type-decision');
  });

  it('should show node details on click', async () => {
    const user = userEvent.setup();
    render(<ProcessFlowVisualization flow={mockProcessFlow} />);

    // Click on a node
    const apolloNode = screen.getByTestId('node-node-apollo');
    await user.click(apolloNode);

    // Details should appear in a panel or tooltip
    expect(screen.getByText('Fetched company data from Apollo.io')).toBeInTheDocument();
    expect(screen.getByText(/2500ms/)).toBeInTheDocument();
  });

  it('should render connections between nodes', () => {
    render(<ProcessFlowVisualization flow={mockProcessFlow} />);

    // Check that edges are rendered
    const edges = screen.getAllByTestId(/^edge-/);
    expect(edges.length).toBe(9);
  });

  it('should display edge labels when available', () => {
    render(<ProcessFlowVisualization flow={mockProcessFlow} />);

    // Check for edge labels
    expect(screen.getByText('Yes')).toBeInTheDocument();
    expect(screen.getByText('No')).toBeInTheDocument();
  });

  it('should handle empty flow', () => {
    render(<ProcessFlowVisualization flow={{ nodes: [], edges: [] }} />);

    expect(screen.getByText(/no process flow data/i)).toBeInTheDocument();
  });

  it('should be responsive and adjust to container size', () => {
    const { container } = render(<ProcessFlowVisualization flow={mockProcessFlow} />);

    const flowContainer = container.querySelector('.flow-container');
    expect(flowContainer).toHaveClass('responsive');
  });

  it('should support zoom controls', async () => {
    const user = userEvent.setup();
    render(<ProcessFlowVisualization flow={mockProcessFlow} />);

    // Find zoom controls
    const zoomInButton = screen.getByRole('button', { name: /zoom in/i });
    const zoomOutButton = screen.getByRole('button', { name: /zoom out/i });
    const resetButton = screen.getByRole('button', { name: /reset/i });

    expect(zoomInButton).toBeInTheDocument();
    expect(zoomOutButton).toBeInTheDocument();
    expect(resetButton).toBeInTheDocument();

    // Click zoom in
    await user.click(zoomInButton);

    // Check that zoom level changed (implementation-specific)
    const flowContainer = screen.getByTestId('flow-visualization');
    expect(flowContainer).toHaveAttribute('data-zoom');
  });

  it('should highlight the current active node', () => {
    render(<ProcessFlowVisualization flow={mockProcessFlow} />);

    // The in_progress node should be highlighted
    const inProgressNode = screen.getByTestId('node-node-resolve');
    expect(inProgressNode).toHaveClass('node-active');
  });

  it('should support keyboard navigation between nodes', async () => {
    const user = userEvent.setup();
    render(<ProcessFlowVisualization flow={mockProcessFlow} />);

    // Tab to first node
    await user.tab();

    // Should focus on a node
    const focusedElement = document.activeElement;
    expect(focusedElement?.getAttribute('data-testid')).toMatch(/^node-/);

    // Arrow key navigation
    await user.keyboard('{ArrowRight}');

    // Should focus on next node
    const newFocusedElement = document.activeElement;
    expect(newFocusedElement).not.toBe(focusedElement);
  });

  it('should show legend for node types', () => {
    render(<ProcessFlowVisualization flow={mockProcessFlow} />);

    // Check for legend
    expect(screen.getByText(/legend/i)).toBeInTheDocument();
    expect(screen.getByText(/api/i)).toBeInTheDocument();
    expect(screen.getByText(/llm/i)).toBeInTheDocument();
    expect(screen.getByText(/decision/i)).toBeInTheDocument();
  });

  it('should provide fallback for non-JS environments', () => {
    const { container } = render(<ProcessFlowVisualization flow={mockProcessFlow} />);

    // Should have a noscript fallback or static representation
    const fallback = container.querySelector('.flow-fallback');
    expect(fallback).toBeInTheDocument();
  });

  it('should meet WCAG accessibility standards', () => {
    render(<ProcessFlowVisualization flow={mockProcessFlow} />);

    // Check for proper ARIA attributes
    const visualization = screen.getByRole('img', { name: /process flow diagram/i });
    expect(visualization).toHaveAttribute('aria-describedby');

    // Check for keyboard navigability
    const nodes = screen.getAllByRole('button');
    nodes.forEach((node) => {
      expect(node).toHaveAttribute('tabIndex');
    });
  });

  it('should display duration on nodes when available', () => {
    render(<ProcessFlowVisualization flow={mockProcessFlow} />);

    // Duration should be visible on completed nodes
    const apolloNode = screen.getByTestId('node-node-apollo');
    expect(apolloNode).toHaveTextContent(/2\.5s|2500ms/);
  });

  it('should animate in-progress nodes', () => {
    render(<ProcessFlowVisualization flow={mockProcessFlow} />);

    const inProgressNode = screen.getByTestId('node-node-resolve');
    expect(inProgressNode).toHaveClass('animating');
  });
});
