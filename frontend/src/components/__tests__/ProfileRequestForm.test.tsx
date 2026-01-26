/**
 * Tests for ProfileRequestForm component.
 * Following TDD - tests written to verify form behavior.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ProfileRequestForm from '../ProfileRequestForm';

describe('ProfileRequestForm', () => {
  const mockOnSubmit = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render all form fields', () => {
    render(
      <ProfileRequestForm
        onSubmit={mockOnSubmit}
        isLoading={false}
      />
    );

    expect(screen.getByLabelText(/company name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/domain/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/industry/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/your email/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /generate profile/i })).toBeInTheDocument();
  });

  it('should display validation errors for empty required fields', async () => {
    const user = userEvent.setup();

    render(
      <ProfileRequestForm
        onSubmit={mockOnSubmit}
        isLoading={false}
      />
    );

    const submitButton = screen.getByRole('button', { name: /generate profile/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/company name is required/i)).toBeInTheDocument();
      expect(screen.getByText(/domain is required/i)).toBeInTheDocument();
      expect(screen.getByText(/email is required/i)).toBeInTheDocument();
    });

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('should validate email format', async () => {
    const user = userEvent.setup();

    render(
      <ProfileRequestForm
        onSubmit={mockOnSubmit}
        isLoading={false}
      />
    );

    const emailInput = screen.getByLabelText(/your email/i);
    await user.type(emailInput, 'invalid-email');
    await user.tab(); // Blur the field

    await waitFor(() => {
      expect(screen.getByText(/please enter a valid email/i)).toBeInTheDocument();
    });
  });

  it('should validate domain format', async () => {
    const user = userEvent.setup();

    render(
      <ProfileRequestForm
        onSubmit={mockOnSubmit}
        isLoading={false}
      />
    );

    const domainInput = screen.getByLabelText(/domain/i);
    await user.type(domainInput, 'not a domain');
    await user.tab(); // Blur the field

    await waitFor(() => {
      expect(screen.getByText(/please enter a valid domain/i)).toBeInTheDocument();
    });
  });

  it('should submit form with valid data', async () => {
    const user = userEvent.setup();

    render(
      <ProfileRequestForm
        onSubmit={mockOnSubmit}
        isLoading={false}
      />
    );

    await user.type(screen.getByLabelText(/company name/i), 'Acme Corp');
    await user.type(screen.getByLabelText(/domain/i), 'acme.com');
    await user.type(screen.getByLabelText(/industry/i), 'Technology');
    await user.type(screen.getByLabelText(/your email/i), 'user@example.com');

    const submitButton = screen.getByRole('button', { name: /generate profile/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        company_name: 'Acme Corp',
        domain: 'acme.com',
        industry: 'Technology',
        requested_by: 'user@example.com',
      });
    });
  });

  it('should sanitize domain input', async () => {
    const user = userEvent.setup();

    render(
      <ProfileRequestForm
        onSubmit={mockOnSubmit}
        isLoading={false}
      />
    );

    await user.type(screen.getByLabelText(/company name/i), 'Acme Corp');
    await user.type(screen.getByLabelText(/domain/i), 'https://www.ACME.com/');
    await user.type(screen.getByLabelText(/your email/i), 'user@example.com');

    const submitButton = screen.getByRole('button', { name: /generate profile/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          domain: 'acme.com',
        })
      );
    });
  });

  it('should disable form when loading', () => {
    render(
      <ProfileRequestForm
        onSubmit={mockOnSubmit}
        isLoading={true}
      />
    );

    expect(screen.getByLabelText(/company name/i)).toBeDisabled();
    expect(screen.getByLabelText(/domain/i)).toBeDisabled();
    expect(screen.getByLabelText(/industry/i)).toBeDisabled();
    expect(screen.getByLabelText(/your email/i)).toBeDisabled();
    expect(screen.getByRole('button', { name: /processing/i })).toBeDisabled();
  });

  it('should display error message when error prop is provided', () => {
    const errorMessage = 'Failed to submit request';

    render(
      <ProfileRequestForm
        onSubmit={mockOnSubmit}
        isLoading={false}
        error={errorMessage}
      />
    );

    expect(screen.getByText(errorMessage)).toBeInTheDocument();
  });

  it('should clear field error when user starts typing', async () => {
    const user = userEvent.setup();

    render(
      <ProfileRequestForm
        onSubmit={mockOnSubmit}
        isLoading={false}
      />
    );

    // Submit empty form to trigger validation errors
    const submitButton = screen.getByRole('button', { name: /generate profile/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/company name is required/i)).toBeInTheDocument();
    });

    // Start typing in company name field
    const companyNameInput = screen.getByLabelText(/company name/i);
    await user.type(companyNameInput, 'Acme');

    // Error should be cleared
    await waitFor(() => {
      expect(screen.queryByText(/company name is required/i)).not.toBeInTheDocument();
    });
  });
});
