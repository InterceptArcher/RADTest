/**
 * Tests for ZoomInfo phone source display in StakeholderMapCard.
 * TDD: Tests written FIRST before implementation.
 *
 * Covers:
 * - ZoomInfo badge shown when phoneSource === 'zoominfo'
 * - Accuracy score shown per phone
 * - All phone types (direct, mobile, company) render correctly
 * - No badge shown for non-ZoomInfo sources
 */

import { render, screen } from '@testing-library/react';
import StakeholderMapCard from '../intelligence/StakeholderMapCard';
import type { StakeholderMap } from '@/types';

const buildStakeholderMap = (overrides?: Partial<StakeholderMap['stakeholders'][0]['contact']>): StakeholderMap => ({
  stakeholders: [
    {
      name: 'Jane Smith',
      title: 'Chief Information Officer',
      roleType: 'CIO',
      bio: 'Experienced CIO.',
      isNewHire: false,
      contact: {
        email: 'jane@example.com',
        directPhone: '+1-555-000-1234',
        mobilePhone: '+1-555-000-5678',
        companyPhone: '+1-555-000-0000',
        linkedinUrl: 'https://linkedin.com/in/janesmith',
        contactAccuracyScore: 92,
        phoneSource: 'zoominfo',
        ...overrides,
      },
      strategicPriorities: [],
    },
  ],
  otherContacts: [],
  lastUpdated: new Date().toISOString(),
  searchPerformed: true,
});

describe('StakeholderMapCard - ZoomInfo Phone Display', () => {
  it('renders direct phone number', () => {
    const map = buildStakeholderMap();
    render(<StakeholderMapCard stakeholderMap={map} />);

    // Expand the card
    const header = screen.getByRole('button');
    header.click();

    expect(screen.getByText(/\+1-555-000-1234/)).toBeInTheDocument();
  });

  it('renders mobile phone number', () => {
    const map = buildStakeholderMap();
    render(<StakeholderMapCard stakeholderMap={map} />);

    const header = screen.getByRole('button');
    header.click();

    expect(screen.getByText(/\+1-555-000-5678/)).toBeInTheDocument();
  });

  it('renders company phone number', () => {
    const map = buildStakeholderMap();
    render(<StakeholderMapCard stakeholderMap={map} />);

    const header = screen.getByRole('button');
    header.click();

    expect(screen.getByText(/\+1-555-000-0000/)).toBeInTheDocument();
  });

  it('shows ZoomInfo badge when phoneSource is zoominfo', () => {
    const map = buildStakeholderMap({ phoneSource: 'zoominfo' });
    render(<StakeholderMapCard stakeholderMap={map} />);

    const header = screen.getByRole('button');
    header.click();

    expect(screen.getByText(/ZoomInfo/i)).toBeInTheDocument();
  });

  it('does NOT show ZoomInfo badge when phoneSource is undefined', () => {
    const map = buildStakeholderMap({ phoneSource: undefined });
    render(<StakeholderMapCard stakeholderMap={map} />);

    const header = screen.getByRole('button');
    header.click();

    expect(screen.queryByText(/ZoomInfo/i)).not.toBeInTheDocument();
  });

  it('shows accuracy score when contactAccuracyScore is provided', () => {
    const map = buildStakeholderMap({ contactAccuracyScore: 92 });
    render(<StakeholderMapCard stakeholderMap={map} />);

    const header = screen.getByRole('button');
    header.click();

    expect(screen.getByText(/92%/)).toBeInTheDocument();
  });

  it('shows Direct label for direct phone', () => {
    const map = buildStakeholderMap({ directPhone: '+1-555-000-1234' });
    render(<StakeholderMapCard stakeholderMap={map} />);

    const header = screen.getByRole('button');
    header.click();

    expect(screen.getByText(/Direct:/i)).toBeInTheDocument();
  });

  it('shows Mobile label for mobile phone', () => {
    const map = buildStakeholderMap({ mobilePhone: '+1-555-000-5678' });
    render(<StakeholderMapCard stakeholderMap={map} />);

    const header = screen.getByRole('button');
    header.click();

    expect(screen.getByText(/Mobile:/i)).toBeInTheDocument();
  });

  it('shows Company label for company phone', () => {
    const map = buildStakeholderMap({ companyPhone: '+1-555-000-0000' });
    render(<StakeholderMapCard stakeholderMap={map} />);

    const header = screen.getByRole('button');
    header.click();

    expect(screen.getByText(/Company:/i)).toBeInTheDocument();
  });

  it('renders fallback phone when no direct/mobile/company phones exist', () => {
    const map = buildStakeholderMap({
      directPhone: undefined,
      mobilePhone: undefined,
      companyPhone: undefined,
      phone: '+1-555-999-8888',
      phoneSource: undefined,
    });
    render(<StakeholderMapCard stakeholderMap={map} />);

    const header = screen.getByRole('button');
    header.click();

    expect(screen.getByText(/\+1-555-999-8888/)).toBeInTheDocument();
  });
});
