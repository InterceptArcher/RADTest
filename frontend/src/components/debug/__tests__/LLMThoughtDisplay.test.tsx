/**
 * Tests for LLMThoughtDisplay component.
 * Feature 020: Display ChatGPT Thought Process
 * Following TDD - tests written first.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LLMThoughtDisplay from '../LLMThoughtDisplay';
import type { LLMThoughtProcess } from '@/types';

describe('LLMThoughtDisplay', () => {
  const mockLLMThoughtProcesses: LLMThoughtProcess[] = [
    {
      id: 'llm-1',
      taskName: 'Data Discrepancy Resolution',
      model: 'gpt-4',
      startTime: '2024-01-15T10:00:10Z',
      endTime: '2024-01-15T10:00:15Z',
      steps: [
        {
          id: 'step-1',
          step: 1,
          action: 'Compare Data Sources',
          reasoning: 'The employee count differs between Apollo.io (500) and PeopleDataLabs (450). Need to determine which source is more reliable.',
          input: {
            apollo: { employee_count: 500 },
            pdl: { employee_count: 450 },
          },
          output: {
            discrepancy: 'employee_count',
            sources: ['Apollo.io', 'PeopleDataLabs'],
          },
          confidence: 0.9,
        },
        {
          id: 'step-2',
          step: 2,
          action: 'Evaluate Source Reliability',
          reasoning: 'Apollo.io data is more recent (updated 2 days ago) vs PeopleDataLabs (updated 30 days ago). Recent data typically more accurate for employee count.',
          input: {
            apollo_last_updated: '2024-01-13',
            pdl_last_updated: '2023-12-15',
          },
          output: {
            more_reliable: 'Apollo.io',
            reason: 'More recent update',
          },
          confidence: 0.85,
        },
        {
          id: 'step-3',
          step: 3,
          action: 'Make Final Decision',
          reasoning: 'Based on data recency, selecting Apollo.io value of 500 employees as the validated data point.',
          output: {
            selected_value: 500,
            source: 'Apollo.io',
          },
          confidence: 0.88,
        },
      ],
      finalDecision: 'Selected employee count of 500 from Apollo.io based on data recency.',
      discrepanciesResolved: ['employee_count'],
    },
    {
      id: 'llm-2',
      taskName: 'Revenue Validation',
      model: 'gpt-4',
      startTime: '2024-01-15T10:00:20Z',
      steps: [
        {
          id: 'step-1',
          step: 1,
          action: 'Validate Revenue Range',
          reasoning: 'Checking if reported revenue of $50M is consistent with company size of 500 employees.',
          confidence: 0.75,
        },
      ],
      finalDecision: 'Revenue of $50M validated as consistent with company profile.',
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render LLM thought display with title', () => {
    render(<LLMThoughtDisplay thoughtProcesses={mockLLMThoughtProcesses} />);

    expect(screen.getByText(/llm thought process/i)).toBeInTheDocument();
  });

  it('should display all thought processes', () => {
    render(<LLMThoughtDisplay thoughtProcesses={mockLLMThoughtProcesses} />);

    expect(screen.getByText('Data Discrepancy Resolution')).toBeInTheDocument();
    expect(screen.getByText('Revenue Validation')).toBeInTheDocument();
  });

  it('should show model name for each process', () => {
    render(<LLMThoughtDisplay thoughtProcesses={mockLLMThoughtProcesses} />);

    const modelLabels = screen.getAllByText(/gpt-4/i);
    expect(modelLabels.length).toBeGreaterThanOrEqual(2);
  });

  it('should allow expanding/collapsing thought process details', async () => {
    const user = userEvent.setup();
    render(<LLMThoughtDisplay thoughtProcesses={mockLLMThoughtProcesses} />);

    // Steps should be hidden initially
    expect(screen.queryByText('Compare Data Sources')).not.toBeInTheDocument();

    // Expand first process
    const expandButton = screen.getByTestId('expand-llm-1');
    await user.click(expandButton);

    // Steps should be visible
    expect(screen.getByText('Compare Data Sources')).toBeInTheDocument();
    expect(screen.getByText('Evaluate Source Reliability')).toBeInTheDocument();
    expect(screen.getByText('Make Final Decision')).toBeInTheDocument();

    // Collapse
    await user.click(expandButton);

    await waitFor(() => {
      expect(screen.queryByText('Compare Data Sources')).not.toBeInTheDocument();
    });
  });

  it('should display reasoning for each step', async () => {
    const user = userEvent.setup();
    render(<LLMThoughtDisplay thoughtProcesses={mockLLMThoughtProcesses} />);

    // Expand first process
    const expandButton = screen.getByTestId('expand-llm-1');
    await user.click(expandButton);

    // Expand first step
    const stepButton = screen.getByTestId('expand-step-1');
    await user.click(stepButton);

    // Reasoning should be visible
    expect(screen.getByText(/employee count differs/i)).toBeInTheDocument();
  });

  it('should display confidence scores', async () => {
    const user = userEvent.setup();
    render(<LLMThoughtDisplay thoughtProcesses={mockLLMThoughtProcesses} />);

    // Expand first process
    const expandButton = screen.getByTestId('expand-llm-1');
    await user.click(expandButton);

    // Confidence scores should be visible
    expect(screen.getByText(/90%/)).toBeInTheDocument();
    expect(screen.getByText(/85%/)).toBeInTheDocument();
  });

  it('should display final decision prominently', async () => {
    const user = userEvent.setup();
    render(<LLMThoughtDisplay thoughtProcesses={mockLLMThoughtProcesses} />);

    // Expand first process
    const expandButton = screen.getByTestId('expand-llm-1');
    await user.click(expandButton);

    // Final decision should be visible
    const finalDecision = screen.getByTestId('final-decision-llm-1');
    expect(finalDecision).toHaveTextContent(/500 from Apollo.io/);
  });

  it('should display resolved discrepancies', async () => {
    const user = userEvent.setup();
    render(<LLMThoughtDisplay thoughtProcesses={mockLLMThoughtProcesses} />);

    // Expand first process
    const expandButton = screen.getByTestId('expand-llm-1');
    await user.click(expandButton);

    // Discrepancies resolved should be listed
    expect(screen.getByText(/employee_count/)).toBeInTheDocument();
  });

  it('should show step numbers in sequence', async () => {
    const user = userEvent.setup();
    render(<LLMThoughtDisplay thoughtProcesses={mockLLMThoughtProcesses} />);

    // Expand first process
    const expandButton = screen.getByTestId('expand-llm-1');
    await user.click(expandButton);

    // Step numbers should be visible
    expect(screen.getByText(/step 1/i)).toBeInTheDocument();
    expect(screen.getByText(/step 2/i)).toBeInTheDocument();
    expect(screen.getByText(/step 3/i)).toBeInTheDocument();
  });

  it('should handle empty thought processes array', () => {
    render(<LLMThoughtDisplay thoughtProcesses={[]} />);

    expect(screen.getByText(/no llm thought processes/i)).toBeInTheDocument();
  });

  it('should display input/output data when available', async () => {
    const user = userEvent.setup();
    render(<LLMThoughtDisplay thoughtProcesses={mockLLMThoughtProcesses} />);

    // Expand first process and first step
    const expandButton = screen.getByTestId('expand-llm-1');
    await user.click(expandButton);

    const stepButton = screen.getByTestId('expand-step-1');
    await user.click(stepButton);

    // Input and output should be visible
    expect(screen.getByText(/input/i)).toBeInTheDocument();
    expect(screen.getByText(/output/i)).toBeInTheDocument();
  });

  it('should show tooltips for complex terms', async () => {
    const user = userEvent.setup();
    render(<LLMThoughtDisplay thoughtProcesses={mockLLMThoughtProcesses} />);

    // Check for tooltip on confidence
    const confidenceLabel = screen.getByText(/confidence/i);
    await user.hover(confidenceLabel);

    await waitFor(() => {
      expect(screen.getByRole('tooltip')).toBeInTheDocument();
    });
  });

  it('should be accessible with screen readers', () => {
    render(<LLMThoughtDisplay thoughtProcesses={mockLLMThoughtProcesses} />);

    // Check for proper ARIA labels
    const section = screen.getByRole('region', { name: /llm thought process/i });
    expect(section).toBeInTheDocument();
  });

  it('should display timestamps for thought processes', async () => {
    const user = userEvent.setup();
    render(<LLMThoughtDisplay thoughtProcesses={mockLLMThoughtProcesses} />);

    // Expand first process
    const expandButton = screen.getByTestId('expand-llm-1');
    await user.click(expandButton);

    // Start and end times should be visible
    expect(screen.getByText(/started/i)).toBeInTheDocument();
    expect(screen.getByText(/completed/i)).toBeInTheDocument();
  });
});
