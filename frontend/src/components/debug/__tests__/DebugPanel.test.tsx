/**
 * Tests for DebugPanel component.
 * Feature 018: Debugging UI for Process Inspection
 * Following TDD - tests written first.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DebugPanel from '../DebugPanel';
import type { ProcessStep } from '@/types';

describe('DebugPanel', () => {
  const mockProcessSteps: ProcessStep[] = [
    {
      id: 'step-1',
      name: 'Data Collection',
      description: 'Gathering data from external APIs',
      status: 'completed',
      startTime: '2024-01-15T10:00:00Z',
      endTime: '2024-01-15T10:00:05Z',
      duration: 5000,
      metadata: { source: 'Apollo.io' },
    },
    {
      id: 'step-2',
      name: 'Data Validation',
      description: 'Validating collected data with LLM agents',
      status: 'in_progress',
      startTime: '2024-01-15T10:00:05Z',
      metadata: { agent: 'validator-1' },
    },
    {
      id: 'step-3',
      name: 'Conflict Resolution',
      description: 'Resolving data discrepancies',
      status: 'pending',
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render debug panel with title', () => {
    render(<DebugPanel steps={mockProcessSteps} />);

    expect(screen.getByText(/debug mode/i)).toBeInTheDocument();
    expect(screen.getByText(/process inspection/i)).toBeInTheDocument();
  });

  it('should display all process steps', () => {
    render(<DebugPanel steps={mockProcessSteps} />);

    expect(screen.getByText('Data Collection')).toBeInTheDocument();
    expect(screen.getByText('Data Validation')).toBeInTheDocument();
    expect(screen.getByText('Conflict Resolution')).toBeInTheDocument();
  });

  it('should show step status indicators', () => {
    render(<DebugPanel steps={mockProcessSteps} />);

    // Check for status indicators
    const completedIndicator = screen.getByTestId('status-step-1');
    const inProgressIndicator = screen.getByTestId('status-step-2');
    const pendingIndicator = screen.getByTestId('status-step-3');

    expect(completedIndicator).toHaveClass('status-completed');
    expect(inProgressIndicator).toHaveClass('status-in_progress');
    expect(pendingIndicator).toHaveClass('status-pending');
  });

  it('should allow expanding/collapsing step details', async () => {
    const user = userEvent.setup();
    render(<DebugPanel steps={mockProcessSteps} />);

    // Details should be hidden initially
    expect(screen.queryByText('Gathering data from external APIs')).not.toBeInTheDocument();

    // Click to expand first step
    const expandButton = screen.getByTestId('expand-step-1');
    await user.click(expandButton);

    // Details should now be visible
    expect(screen.getByText('Gathering data from external APIs')).toBeInTheDocument();

    // Click again to collapse
    await user.click(expandButton);

    // Details should be hidden again
    await waitFor(() => {
      expect(screen.queryByText('Gathering data from external APIs')).not.toBeInTheDocument();
    });
  });

  it('should display step duration for completed steps', async () => {
    const user = userEvent.setup();
    render(<DebugPanel steps={mockProcessSteps} />);

    // Expand first step
    const expandButton = screen.getByTestId('expand-step-1');
    await user.click(expandButton);

    // Should show duration
    expect(screen.getByText(/5000ms/)).toBeInTheDocument();
  });

  it('should display step metadata when expanded', async () => {
    const user = userEvent.setup();
    render(<DebugPanel steps={mockProcessSteps} />);

    // Expand first step
    const expandButton = screen.getByTestId('expand-step-1');
    await user.click(expandButton);

    // Should show metadata
    expect(screen.getByText(/Apollo\.io/)).toBeInTheDocument();
  });

  it('should handle empty steps array', () => {
    render(<DebugPanel steps={[]} />);

    expect(screen.getByText(/no process steps/i)).toBeInTheDocument();
  });

  it('should show expand all/collapse all buttons', async () => {
    const user = userEvent.setup();
    render(<DebugPanel steps={mockProcessSteps} />);

    const expandAllButton = screen.getByRole('button', { name: /expand all/i });
    expect(expandAllButton).toBeInTheDocument();

    // Click expand all
    await user.click(expandAllButton);

    // All details should be visible
    expect(screen.getByText('Gathering data from external APIs')).toBeInTheDocument();
    expect(screen.getByText('Validating collected data with LLM agents')).toBeInTheDocument();
    expect(screen.getByText('Resolving data discrepancies')).toBeInTheDocument();

    // Collapse all button should appear
    const collapseAllButton = screen.getByRole('button', { name: /collapse all/i });
    await user.click(collapseAllButton);

    // All details should be hidden
    await waitFor(() => {
      expect(screen.queryByText('Gathering data from external APIs')).not.toBeInTheDocument();
    });
  });

  it('should display timestamps for steps with timing info', async () => {
    const user = userEvent.setup();
    render(<DebugPanel steps={mockProcessSteps} />);

    // Expand first step
    const expandButton = screen.getByTestId('expand-step-1');
    await user.click(expandButton);

    // Should show start and end times
    expect(screen.getByText(/start:/i)).toBeInTheDocument();
    expect(screen.getByText(/end:/i)).toBeInTheDocument();
  });

  it('should be accessible with keyboard navigation', async () => {
    const user = userEvent.setup();
    render(<DebugPanel steps={mockProcessSteps} />);

    // Tab to first expand button and press Enter
    await user.tab();
    await user.tab();
    await user.keyboard('{Enter}');

    // Step should be expanded
    expect(screen.getByText('Gathering data from external APIs')).toBeInTheDocument();
  });
});
