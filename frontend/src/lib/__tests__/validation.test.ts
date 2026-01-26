/**
 * Tests for form validation utilities.
 * Following TDD - tests written to verify validation logic.
 */

import {
  validateProfileRequest,
  hasErrors,
  sanitizeDomain,
} from '../validation';
import type { CompanyProfileRequest } from '@/types';

describe('validateProfileRequest', () => {
  it('should return no errors for valid data', () => {
    const validData: CompanyProfileRequest = {
      company_name: 'Acme Corp',
      domain: 'acme.com',
      industry: 'Technology',
      requested_by: 'user@example.com',
    };

    const errors = validateProfileRequest(validData);
    expect(Object.keys(errors)).toHaveLength(0);
  });

  it('should require company_name', () => {
    const data: Partial<CompanyProfileRequest> = {
      domain: 'acme.com',
      requested_by: 'user@example.com',
    };

    const errors = validateProfileRequest(data);
    expect(errors.company_name).toBeDefined();
  });

  it('should reject empty company_name', () => {
    const data: Partial<CompanyProfileRequest> = {
      company_name: '   ',
      domain: 'acme.com',
      requested_by: 'user@example.com',
    };

    const errors = validateProfileRequest(data);
    expect(errors.company_name).toBeDefined();
  });

  it('should reject company_name longer than 500 characters', () => {
    const data: Partial<CompanyProfileRequest> = {
      company_name: 'a'.repeat(501),
      domain: 'acme.com',
      requested_by: 'user@example.com',
    };

    const errors = validateProfileRequest(data);
    expect(errors.company_name).toBeDefined();
  });

  it('should require domain', () => {
    const data: Partial<CompanyProfileRequest> = {
      company_name: 'Acme Corp',
      requested_by: 'user@example.com',
    };

    const errors = validateProfileRequest(data);
    expect(errors.domain).toBeDefined();
  });

  it('should reject invalid domain format', () => {
    const invalidDomains = [
      'not a domain',
      'invalid..com',
      '.com',
      'domain.',
      'http://example.com',
    ];

    invalidDomains.forEach((domain) => {
      const data: Partial<CompanyProfileRequest> = {
        company_name: 'Acme Corp',
        domain,
        requested_by: 'user@example.com',
      };

      const errors = validateProfileRequest(data);
      expect(errors.domain).toBeDefined();
    });
  });

  it('should accept valid domain formats', () => {
    const validDomains = [
      'example.com',
      'subdomain.example.com',
      'my-domain.com',
      'example.co.uk',
    ];

    validDomains.forEach((domain) => {
      const data: CompanyProfileRequest = {
        company_name: 'Acme Corp',
        domain,
        requested_by: 'user@example.com',
      };

      const errors = validateProfileRequest(data);
      expect(errors.domain).toBeUndefined();
    });
  });

  it('should reject domain longer than 255 characters', () => {
    const data: Partial<CompanyProfileRequest> = {
      company_name: 'Acme Corp',
      domain: 'a'.repeat(252) + '.com', // 256 characters total
      requested_by: 'user@example.com',
    };

    const errors = validateProfileRequest(data);
    expect(errors.domain).toBeDefined();
  });

  it('should allow optional industry field', () => {
    const data: CompanyProfileRequest = {
      company_name: 'Acme Corp',
      domain: 'acme.com',
      requested_by: 'user@example.com',
    };

    const errors = validateProfileRequest(data);
    expect(errors.industry).toBeUndefined();
  });

  it('should reject industry longer than 200 characters', () => {
    const data: Partial<CompanyProfileRequest> = {
      company_name: 'Acme Corp',
      domain: 'acme.com',
      industry: 'a'.repeat(201),
      requested_by: 'user@example.com',
    };

    const errors = validateProfileRequest(data);
    expect(errors.industry).toBeDefined();
  });

  it('should require requested_by email', () => {
    const data: Partial<CompanyProfileRequest> = {
      company_name: 'Acme Corp',
      domain: 'acme.com',
    };

    const errors = validateProfileRequest(data);
    expect(errors.requested_by).toBeDefined();
  });

  it('should reject invalid email format', () => {
    const invalidEmails = [
      'not an email',
      '@example.com',
      'user@',
      'user',
      'user@domain',
    ];

    invalidEmails.forEach((email) => {
      const data: Partial<CompanyProfileRequest> = {
        company_name: 'Acme Corp',
        domain: 'acme.com',
        requested_by: email,
      };

      const errors = validateProfileRequest(data);
      expect(errors.requested_by).toBeDefined();
    });
  });

  it('should accept valid email formats', () => {
    const validEmails = [
      'user@example.com',
      'user.name@example.com',
      'user+tag@example.co.uk',
    ];

    validEmails.forEach((email) => {
      const data: CompanyProfileRequest = {
        company_name: 'Acme Corp',
        domain: 'acme.com',
        requested_by: email,
      };

      const errors = validateProfileRequest(data);
      expect(errors.requested_by).toBeUndefined();
    });
  });
});

describe('hasErrors', () => {
  it('should return true if errors object has keys', () => {
    const errors = { company_name: 'Required' };
    expect(hasErrors(errors)).toBe(true);
  });

  it('should return false if errors object is empty', () => {
    const errors = {};
    expect(hasErrors(errors)).toBe(false);
  });
});

describe('sanitizeDomain', () => {
  it('should remove http protocol', () => {
    expect(sanitizeDomain('http://example.com')).toBe('example.com');
  });

  it('should remove https protocol', () => {
    expect(sanitizeDomain('https://example.com')).toBe('example.com');
  });

  it('should remove www prefix', () => {
    expect(sanitizeDomain('www.example.com')).toBe('example.com');
  });

  it('should remove protocol and www', () => {
    expect(sanitizeDomain('https://www.example.com')).toBe('example.com');
  });

  it('should remove trailing slash', () => {
    expect(sanitizeDomain('example.com/')).toBe('example.com');
  });

  it('should remove paths', () => {
    expect(sanitizeDomain('example.com/path/to/page')).toBe('example.com');
  });

  it('should convert to lowercase', () => {
    expect(sanitizeDomain('EXAMPLE.COM')).toBe('example.com');
  });

  it('should trim whitespace', () => {
    expect(sanitizeDomain('  example.com  ')).toBe('example.com');
  });

  it('should handle complex URLs', () => {
    expect(sanitizeDomain('https://www.EXAMPLE.com/path?query=1')).toBe('example.com');
  });
});
