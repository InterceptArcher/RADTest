/**
 * Form validation utilities.
 */

import type { CompanyProfileRequest, FormErrors } from '@/types';

/**
 * Validate company profile request form data.
 *
 * @param data - Form data to validate
 * @returns Object with validation errors, or empty object if valid
 */
export function validateProfileRequest(
  data: Partial<CompanyProfileRequest>
): FormErrors {
  const errors: FormErrors = {};

  // Validate company name
  if (!data.company_name || data.company_name.trim().length === 0) {
    errors.company_name = 'Company name is required';
  } else if (data.company_name.length > 500) {
    errors.company_name = 'Company name must be less than 500 characters';
  }

  // Validate domain
  if (!data.domain || data.domain.trim().length === 0) {
    errors.domain = 'Domain is required';
  } else if (data.domain.trim().length > 255) {
    errors.domain = 'Domain must be less than 255 characters';
  } else if (!/^[a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,}$/i.test(data.domain.trim())) {
    errors.domain = 'Please enter a valid domain (e.g., example.com)';
  }

  // Validate industry (optional)
  if (data.industry && data.industry.length > 200) {
    errors.industry = 'Industry must be less than 200 characters';
  }

  // Validate requested_by (email)
  if (!data.requested_by || data.requested_by.trim().length === 0) {
    errors.requested_by = 'Email is required';
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.requested_by)) {
    errors.requested_by = 'Please enter a valid email address';
  }

  return errors;
}

/**
 * Check if form has any validation errors.
 *
 * @param errors - Form errors object
 * @returns True if there are errors, false otherwise
 */
export function hasErrors(errors: FormErrors): boolean {
  return Object.keys(errors).length > 0;
}

/**
 * Sanitize domain input (remove protocol, paths, etc.)
 *
 * @param domain - Raw domain input
 * @returns Sanitized domain
 */
export function sanitizeDomain(domain: string): string {
  let sanitized = domain.trim().toLowerCase();

  // Remove protocol
  sanitized = sanitized.replace(/^(https?:\/\/)?(www\.)?/, '');

  // Remove trailing slash and path
  sanitized = sanitized.replace(/\/.*$/, '');

  return sanitized;
}
