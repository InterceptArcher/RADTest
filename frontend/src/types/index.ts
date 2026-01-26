/**
 * Type definitions for the RADTest application.
 */

/**
 * Company profile request payload.
 */
export interface CompanyProfileRequest {
  company_name: string;
  domain: string;
  industry?: string;
  requested_by: string;
}

/**
 * Profile request response from backend.
 */
export interface ProfileRequestResponse {
  status: string;
  job_id: string;
  message?: string;
}

/**
 * Error response from backend.
 */
export interface ErrorResponse {
  error: string;
  detail?: string | any;
}

/**
 * Processing status for a job.
 */
export interface JobStatus {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress?: number;
  current_step?: string;
  result?: ProfileResult;
  error?: string;
}

/**
 * Final profile result.
 */
export interface ProfileResult {
  success: boolean;
  company_name: string;
  domain: string;
  slideshow_url?: string;
  confidence_score: number;
  finalize_record_id?: string;
  validated_data?: CompanyData;
}

/**
 * Validated company data.
 */
export interface CompanyData {
  company_name: string;
  domain: string;
  industry?: string;
  employee_count?: number | string;
  revenue?: string;
  headquarters?: string;
  founded_year?: number | string;
  ceo?: string;
  technology?: string[];
  target_market?: string;
  geographic_reach?: string;
  contacts?: {
    website?: string;
    linkedin?: string;
    email?: string;
  };
}

/**
 * Form validation errors.
 */
export interface FormErrors {
  company_name?: string;
  domain?: string;
  industry?: string;
  requested_by?: string;
}
