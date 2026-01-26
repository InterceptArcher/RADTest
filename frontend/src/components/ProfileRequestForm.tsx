/**
 * Company profile request form component.
 * Collects company information and submits to backend API.
 */

'use client';

import { useState, FormEvent, ChangeEvent } from 'react';
import type { CompanyProfileRequest, FormErrors } from '@/types';
import { validateProfileRequest, hasErrors, sanitizeDomain } from '@/lib/validation';

interface ProfileRequestFormProps {
  onSubmit: (data: CompanyProfileRequest) => void;
  isLoading: boolean;
  error?: string | null;
}

export default function ProfileRequestForm({
  onSubmit,
  isLoading,
  error,
}: ProfileRequestFormProps) {
  const [formData, setFormData] = useState<Partial<CompanyProfileRequest>>({
    company_name: '',
    domain: '',
    industry: '',
    requested_by: '',
  });

  const [errors, setErrors] = useState<FormErrors>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  /**
   * Handle input change.
   */
  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;

    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));

    // Clear error for this field when user starts typing
    if (errors[name as keyof FormErrors]) {
      setErrors((prev) => ({
        ...prev,
        [name]: undefined,
      }));
    }
  };

  /**
   * Handle input blur (mark field as touched).
   */
  const handleBlur = (e: ChangeEvent<HTMLInputElement>) => {
    const { name } = e.target;
    setTouched((prev) => ({
      ...prev,
      [name]: true,
    }));

    // Validate on blur
    const validationErrors = validateProfileRequest(formData);
    if (validationErrors[name as keyof FormErrors]) {
      setErrors((prev) => ({
        ...prev,
        [name]: validationErrors[name as keyof FormErrors],
      }));
    }
  };

  /**
   * Handle form submission.
   */
  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    // Sanitize domain
    const sanitizedData = {
      ...formData,
      domain: formData.domain ? sanitizeDomain(formData.domain) : '',
    };

    // Validate all fields
    const validationErrors = validateProfileRequest(sanitizedData);

    if (hasErrors(validationErrors)) {
      setErrors(validationErrors);
      // Mark all fields as touched
      setTouched({
        company_name: true,
        domain: true,
        industry: true,
        requested_by: true,
      });
      return;
    }

    // Submit form
    onSubmit(sanitizedData as CompanyProfileRequest);
  };

  /**
   * Check if field should show error.
   */
  const shouldShowError = (fieldName: keyof FormErrors): boolean => {
    return touched[fieldName] && !!errors[fieldName];
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Company Name */}
      <div>
        <label
          htmlFor="company_name"
          className="block text-sm font-medium text-gray-700 mb-2"
        >
          Company Name <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          id="company_name"
          name="company_name"
          value={formData.company_name}
          onChange={handleChange}
          onBlur={handleBlur}
          disabled={isLoading}
          className={`
            w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2
            ${
              shouldShowError('company_name')
                ? 'border-red-500 focus:ring-red-500'
                : 'border-gray-300 focus:ring-primary-500'
            }
            ${isLoading ? 'bg-gray-100 cursor-not-allowed' : ''}
          `}
          placeholder="e.g., Acme Corporation"
          aria-invalid={shouldShowError('company_name')}
          aria-describedby={
            shouldShowError('company_name') ? 'company_name-error' : undefined
          }
        />
        {shouldShowError('company_name') && (
          <p
            id="company_name-error"
            className="mt-1 text-sm text-red-600"
            role="alert"
          >
            {errors.company_name}
          </p>
        )}
      </div>

      {/* Domain */}
      <div>
        <label
          htmlFor="domain"
          className="block text-sm font-medium text-gray-700 mb-2"
        >
          Domain <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          id="domain"
          name="domain"
          value={formData.domain}
          onChange={handleChange}
          onBlur={handleBlur}
          disabled={isLoading}
          className={`
            w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2
            ${
              shouldShowError('domain')
                ? 'border-red-500 focus:ring-red-500'
                : 'border-gray-300 focus:ring-primary-500'
            }
            ${isLoading ? 'bg-gray-100 cursor-not-allowed' : ''}
          `}
          placeholder="e.g., acme.com"
          aria-invalid={shouldShowError('domain')}
          aria-describedby={shouldShowError('domain') ? 'domain-error' : undefined}
        />
        {shouldShowError('domain') && (
          <p
            id="domain-error"
            className="mt-1 text-sm text-red-600"
            role="alert"
          >
            {errors.domain}
          </p>
        )}
        <p className="mt-1 text-xs text-gray-500">
          Enter domain without protocol (e.g., example.com)
        </p>
      </div>

      {/* Industry (Optional) */}
      <div>
        <label
          htmlFor="industry"
          className="block text-sm font-medium text-gray-700 mb-2"
        >
          Industry <span className="text-gray-400">(Optional)</span>
        </label>
        <input
          type="text"
          id="industry"
          name="industry"
          value={formData.industry}
          onChange={handleChange}
          onBlur={handleBlur}
          disabled={isLoading}
          className={`
            w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2
            ${
              shouldShowError('industry')
                ? 'border-red-500 focus:ring-red-500'
                : 'border-gray-300 focus:ring-primary-500'
            }
            ${isLoading ? 'bg-gray-100 cursor-not-allowed' : ''}
          `}
          placeholder="e.g., Technology, Healthcare"
          aria-invalid={shouldShowError('industry')}
          aria-describedby={shouldShowError('industry') ? 'industry-error' : undefined}
        />
        {shouldShowError('industry') && (
          <p
            id="industry-error"
            className="mt-1 text-sm text-red-600"
            role="alert"
          >
            {errors.industry}
          </p>
        )}
      </div>

      {/* Requested By (Email) */}
      <div>
        <label
          htmlFor="requested_by"
          className="block text-sm font-medium text-gray-700 mb-2"
        >
          Your Email <span className="text-red-500">*</span>
        </label>
        <input
          type="email"
          id="requested_by"
          name="requested_by"
          value={formData.requested_by}
          onChange={handleChange}
          onBlur={handleBlur}
          disabled={isLoading}
          className={`
            w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2
            ${
              shouldShowError('requested_by')
                ? 'border-red-500 focus:ring-red-500'
                : 'border-gray-300 focus:ring-primary-500'
            }
            ${isLoading ? 'bg-gray-100 cursor-not-allowed' : ''}
          `}
          placeholder="your.email@example.com"
          aria-invalid={shouldShowError('requested_by')}
          aria-describedby={
            shouldShowError('requested_by') ? 'requested_by-error' : undefined
          }
        />
        {shouldShowError('requested_by') && (
          <p
            id="requested_by-error"
            className="mt-1 text-sm text-red-600"
            role="alert"
          >
            {errors.requested_by}
          </p>
        )}
      </div>

      {/* Error Alert */}
      {error && (
        <div
          className="p-4 bg-red-50 border border-red-200 rounded-lg"
          role="alert"
        >
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isLoading}
        className={`
          w-full py-3 px-6 rounded-lg font-medium text-white
          transition-colors duration-200
          ${
            isLoading
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2'
          }
        `}
      >
        {isLoading ? (
          <span className="flex items-center justify-center">
            <svg
              className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              ></circle>
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              ></path>
            </svg>
            Processing...
          </span>
        ) : (
          'Generate Profile'
        )}
      </button>

      <p className="text-xs text-center text-gray-500">
        Profile generation typically takes 2-5 minutes
      </p>
    </form>
  );
}
