/**
 * Tests for AddCompanyForm — seller dropdown and email label.
 * TDD: Verifies that the form includes a seller assignment dropdown
 * and the email label reads "Salesperson Email".
 */

import { render, screen } from '@testing-library/react';

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

// Mock useJobs
jest.mock('@/hooks/useJobs', () => ({
  useJobs: () => ({
    addJob: jest.fn(),
  }),
}));

// Mock useSellers
jest.mock('@/hooks/useSellers', () => ({
  useSellers: () => ({
    sellers: [
      { id: 'seller-1', name: 'Acme Corp', created_at: '2026-01-01' },
      { id: 'seller-2', name: 'Beta Inc', created_at: '2026-01-02' },
    ],
  }),
}));

// Mock API client
jest.mock('@/lib/api', () => ({
  apiClient: {
    submitProfileRequest: jest.fn(),
  },
}));

// Mock validation
jest.mock('@/lib/validation', () => ({
  sanitizeDomain: (d: string) => d,
}));

import AddCompanyForm from '../jobs/AddCompanyForm';

describe('AddCompanyForm', () => {
  it('should render a seller assignment dropdown', () => {
    render(<AddCompanyForm />);
    expect(screen.getByLabelText(/seller/i)).toBeInTheDocument();
  });

  it('should include "None" option in seller dropdown', () => {
    render(<AddCompanyForm />);
    const select = screen.getByLabelText(/seller/i) as HTMLSelectElement;
    const options = Array.from(select.options).map((o) => o.text);
    expect(options).toContain('None (Local Only)');
  });

  it('should list all sellers in dropdown', () => {
    render(<AddCompanyForm />);
    const select = screen.getByLabelText(/seller/i) as HTMLSelectElement;
    const options = Array.from(select.options).map((o) => o.text);
    expect(options).toContain('Acme Corp');
    expect(options).toContain('Beta Inc');
  });

  it('should label the email field as "Salesperson Email"', () => {
    render(<AddCompanyForm />);
    expect(screen.getByLabelText(/salesperson email/i)).toBeInTheDocument();
  });
});
