'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useJobs } from '@/hooks/useJobs';
import { useSellers } from '@/hooks/useSellers';
import { apiClient } from '@/lib/api';
import { sanitizeDomain } from '@/lib/validation';

interface FormData {
  companyName: string;
  website: string;
  salespersonName: string;
  email: string;
  sellerId: string;
}

interface FormErrors {
  companyName?: string;
  website?: string;
  salespersonName?: string;
  email?: string;
}

export default function AddCompanyForm() {
  const router = useRouter();
  const { addJob } = useJobs();
  const { sellers, addSellerJob } = useSellers();
  const [formData, setFormData] = useState<FormData>({
    companyName: '',
    website: '',
    salespersonName: '',
    email: '',
    sellerId: '',
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validate = (): boolean => {
    const newErrors: FormErrors = {};

    if (!formData.companyName.trim()) {
      newErrors.companyName = 'Company name is required';
    }

    if (!formData.website.trim()) {
      newErrors.website = 'Website is required';
    } else {
      const domain = sanitizeDomain(formData.website);
      if (!domain || !/^[a-zA-Z0-9][a-zA-Z0-9-]*\.[a-zA-Z]{2,}$/.test(domain)) {
        newErrors.website = 'Please enter a valid domain (e.g., example.com)';
      }
    }

    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Please enter a valid email';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) return;

    setIsSubmitting(true);

    try {
      const domain = sanitizeDomain(formData.website);
      const selectedSeller = sellers.find((s) => s.id === formData.sellerId);

      const response = await apiClient.submitProfileRequest({
        company_name: formData.companyName,
        domain: domain,
        requested_by: formData.email,
        salesperson_name: formData.salespersonName || undefined,
      });

      addJob(response.job_id, {
        company_name: formData.companyName,
        domain: domain,
        requested_by: formData.email,
        salesperson_name: formData.salespersonName || undefined,
      }, formData.sellerId || undefined, selectedSeller?.name);

      if (formData.sellerId) {
        await addSellerJob({
          job_id: response.job_id,
          seller_id: formData.sellerId,
          company_name: formData.companyName,
          domain: domain,
          status: 'pending',
          requested_by: formData.email,
          salesperson_name: formData.salespersonName || undefined,
          created_at: new Date().toISOString(),
        });
      }

      setFormData({ companyName: '', website: '', salespersonName: '', email: '', sellerId: '' });
      router.push('/dashboard/jobs');
    } catch (error) {
      console.error('Failed to submit:', error);
      setErrors({
        companyName:
          error instanceof Error ? error.message : 'Failed to submit request',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Section 1: Company Details */}
      <fieldset className="space-y-3">
        <legend className="text-sm font-semibold text-[#282727] uppercase tracking-wider mb-2">Company Details</legend>
        <div>
          <label htmlFor="companyName" className="block text-sm font-medium text-[#282727] mb-1">
            Company Name <span className="text-primary-500">*</span>
          </label>
          <input
            type="text"
            id="companyName"
            value={formData.companyName}
            onChange={(e) => setFormData({ ...formData, companyName: e.target.value })}
            placeholder="e.g., Microsoft Corporation"
            className={`input-field ${errors.companyName ? 'border-red-300 focus:ring-red-500/20 focus:border-red-500' : ''}`}
          />
          {errors.companyName && (
            <p className="mt-1 text-[11px] text-red-600">{errors.companyName}</p>
          )}
        </div>

        <div>
          <label htmlFor="website" className="block text-sm font-medium text-[#282727] mb-1">
            Website <span className="text-primary-500">*</span>
          </label>
          <input
            type="text"
            id="website"
            value={formData.website}
            onChange={(e) => setFormData({ ...formData, website: e.target.value })}
            placeholder="e.g., microsoft.com"
            className={`input-field ${errors.website ? 'border-red-300 focus:ring-red-500/20 focus:border-red-500' : ''}`}
          />
          {errors.website && (
            <p className="mt-1 text-[11px] text-red-600">{errors.website}</p>
          )}
        </div>
      </fieldset>

      <div className="border-t border-slate-200" />

      {/* Section 2: Assignment */}
      <fieldset className="space-y-3">
        <legend className="text-sm font-semibold text-[#282727] uppercase tracking-wider mb-2">Assignment</legend>
        <div>
          <label htmlFor="sellerId" className="block text-sm font-medium text-[#282727] mb-1">
            Seller <span className="text-[#939393] font-normal">(optional)</span>
          </label>
          <select
            id="sellerId"
            value={formData.sellerId}
            onChange={(e) => setFormData({ ...formData, sellerId: e.target.value })}
            className="input-field"
          >
            <option value="">None (Local Only)</option>
            {sellers.map((seller) => (
              <option key={seller.id} value={seller.id}>{seller.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="salespersonName" className="block text-sm font-medium text-[#282727] mb-1">
            Salesperson <span className="text-[#939393] font-normal">(optional)</span>
          </label>
          <input
            type="text"
            id="salespersonName"
            value={formData.salespersonName}
            onChange={(e) => setFormData({ ...formData, salespersonName: e.target.value })}
            placeholder="e.g., Jane Smith"
            className="input-field"
          />
        </div>

        <div>
          <label htmlFor="email" className="block text-sm font-medium text-[#282727] mb-1">
            Salesperson Email <span className="text-primary-500">*</span>
          </label>
          <input
            type="email"
            id="email"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            placeholder="e.g., salesperson@company.com"
            className={`input-field ${errors.email ? 'border-red-300 focus:ring-red-500/20 focus:border-red-500' : ''}`}
          />
          {errors.email && (
            <p className="mt-1 text-[11px] text-red-600">{errors.email}</p>
          )}
        </div>
      </fieldset>

      <button
        type="submit"
        disabled={isSubmitting}
        className={`btn-primary w-full text-sm ${isSubmitting ? 'opacity-70 cursor-not-allowed' : ''}`}
      >
        {isSubmitting ? (
          <span className="flex items-center justify-center">
            <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            Processing...
          </span>
        ) : (
          'Generate Profile'
        )}
      </button>
    </form>
  );
}
