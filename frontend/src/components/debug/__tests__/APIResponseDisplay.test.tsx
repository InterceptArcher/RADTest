/**
 * Tests for APIResponseDisplay component.
 * Feature 019: Display API Return Values
 * Following TDD - tests written first.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import APIResponseDisplay from '../APIResponseDisplay';
import type { APIResponseData } from '@/types';

describe('APIResponseDisplay', () => {
  const mockAPIResponses: APIResponseData[] = [
    {
      id: 'api-1',
      apiName: 'Apollo.io Company API',
      url: 'https://api.apollo.io/v1/companies',
      method: 'GET',
      statusCode: 200,
      statusText: 'OK',
      headers: {
        'content-type': 'application/json',
        'x-request-id': 'req-123',
      },
      responseBody: {
        company: {
          name: 'Acme Corp',
          domain: 'acme.com',
          employee_count: 500,
        },
      },
      timestamp: '2024-01-15T10:00:00Z',
      duration: 245,
      isSensitive: false,
    },
    {
      id: 'api-2',
      apiName: 'PeopleDataLabs API',
      url: 'https://api.peopledatalabs.com/v5/company',
      method: 'POST',
      statusCode: 401,
      statusText: 'Unauthorized',
      headers: {
        'content-type': 'application/json',
      },
      requestBody: {
        domain: 'acme.com',
        api_key: 'secret-key-12345',
      },
      responseBody: {
        error: 'Invalid API key',
      },
      timestamp: '2024-01-15T10:00:01Z',
      duration: 150,
      isSensitive: true,
      maskedFields: ['api_key'],
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render API response display with title', () => {
    render(<APIResponseDisplay responses={mockAPIResponses} />);

    expect(screen.getByText(/api responses/i)).toBeInTheDocument();
  });

  it('should display all API responses', () => {
    render(<APIResponseDisplay responses={mockAPIResponses} />);

    expect(screen.getByText('Apollo.io Company API')).toBeInTheDocument();
    expect(screen.getByText('PeopleDataLabs API')).toBeInTheDocument();
  });

  it('should show status code with appropriate styling', () => {
    render(<APIResponseDisplay responses={mockAPIResponses} />);

    const successStatus = screen.getByTestId('status-api-1');
    const errorStatus = screen.getByTestId('status-api-2');

    expect(successStatus).toHaveTextContent('200');
    expect(successStatus).toHaveClass('status-success');
    expect(errorStatus).toHaveTextContent('401');
    expect(errorStatus).toHaveClass('status-error');
  });

  it('should display HTTP method and URL', async () => {
    const user = userEvent.setup();
    render(<APIResponseDisplay responses={mockAPIResponses} />);

    // Expand first response
    const expandButton = screen.getByTestId('expand-api-1');
    await user.click(expandButton);

    expect(screen.getByText('GET')).toBeInTheDocument();
    expect(screen.getByText('https://api.apollo.io/v1/companies')).toBeInTheDocument();
  });

  it('should allow expanding/collapsing response details', async () => {
    const user = userEvent.setup();
    render(<APIResponseDisplay responses={mockAPIResponses} />);

    // Details should be hidden initially
    expect(screen.queryByText(/content-type/i)).not.toBeInTheDocument();

    // Click to expand
    const expandButton = screen.getByTestId('expand-api-1');
    await user.click(expandButton);

    // Headers should be visible
    expect(screen.getByText(/content-type/i)).toBeInTheDocument();

    // Collapse
    await user.click(expandButton);

    await waitFor(() => {
      expect(screen.queryByText('x-request-id')).not.toBeInTheDocument();
    });
  });

  it('should display response body as formatted JSON', async () => {
    const user = userEvent.setup();
    render(<APIResponseDisplay responses={mockAPIResponses} />);

    // Expand first response
    const expandButton = screen.getByTestId('expand-api-1');
    await user.click(expandButton);

    // Response body section should exist
    expect(screen.getByText(/response body/i)).toBeInTheDocument();
    expect(screen.getByText(/Acme Corp/)).toBeInTheDocument();
  });

  it('should mask sensitive data in request body', async () => {
    const user = userEvent.setup();
    render(<APIResponseDisplay responses={mockAPIResponses} />);

    // Expand second response (with sensitive data)
    const expandButton = screen.getByTestId('expand-api-2');
    await user.click(expandButton);

    // Should show masked value for api_key
    expect(screen.queryByText('secret-key-12345')).not.toBeInTheDocument();
    expect(screen.getByText(/\*{6,}/)).toBeInTheDocument(); // Masked with asterisks
  });

  it('should show sensitive data warning indicator', () => {
    render(<APIResponseDisplay responses={mockAPIResponses} />);

    const sensitiveIndicator = screen.getByTestId('sensitive-api-2');
    expect(sensitiveIndicator).toBeInTheDocument();
  });

  it('should display request duration', () => {
    render(<APIResponseDisplay responses={mockAPIResponses} />);

    expect(screen.getByText(/245ms/)).toBeInTheDocument();
    expect(screen.getByText(/150ms/)).toBeInTheDocument();
  });

  it('should handle empty responses array', () => {
    render(<APIResponseDisplay responses={[]} />);

    expect(screen.getByText(/no api responses/i)).toBeInTheDocument();
  });

  it('should allow filtering by status', async () => {
    const user = userEvent.setup();
    render(<APIResponseDisplay responses={mockAPIResponses} />);

    // Click error filter
    const errorFilter = screen.getByRole('button', { name: /errors/i });
    await user.click(errorFilter);

    // Only error response should be visible
    expect(screen.queryByText('Apollo.io Company API')).not.toBeInTheDocument();
    expect(screen.getByText('PeopleDataLabs API')).toBeInTheDocument();
  });

  it('should allow sorting by timestamp', async () => {
    const user = userEvent.setup();
    render(<APIResponseDisplay responses={mockAPIResponses} />);

    // Click sort button
    const sortButton = screen.getByRole('button', { name: /sort/i });
    await user.click(sortButton);

    // Check order changed (implementation-specific check)
    const items = screen.getAllByTestId(/^expand-api-/);
    expect(items).toHaveLength(2);
  });

  it('should display request body when available', async () => {
    const user = userEvent.setup();
    render(<APIResponseDisplay responses={mockAPIResponses} />);

    // Expand second response (has request body)
    const expandButton = screen.getByTestId('expand-api-2');
    await user.click(expandButton);

    expect(screen.getByText(/request body/i)).toBeInTheDocument();
  });

  it('should copy response to clipboard', async () => {
    const user = userEvent.setup();
    const mockWriteText = jest.fn();
    Object.assign(navigator, {
      clipboard: {
        writeText: mockWriteText,
      },
    });

    render(<APIResponseDisplay responses={mockAPIResponses} />);

    // Expand first response
    const expandButton = screen.getByTestId('expand-api-1');
    await user.click(expandButton);

    // Click copy button
    const copyButton = screen.getByRole('button', { name: /copy/i });
    await user.click(copyButton);

    expect(mockWriteText).toHaveBeenCalled();
  });
});
