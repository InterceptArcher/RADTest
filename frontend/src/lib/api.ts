/**
 * API client for communicating with the FastAPI backend.
 *
 * IMPORTANT: Backend API URL must be provided via NEXT_PUBLIC_API_URL
 * environment variable. Never hardcode URLs or secrets.
 */

import axios, { AxiosError } from 'axios';
import type {
  CompanyProfileRequest,
  ProfileRequestResponse,
  JobStatus,
  ErrorResponse,
  ContactEnrichResponse,
} from '@/types';

// Get API URL from environment variable with fallback to production backend
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://radtest-backend-4mux.onrender.com';

if (!process.env.NEXT_PUBLIC_API_URL) {
  console.warn(
    'NEXT_PUBLIC_API_URL not defined, using default production backend: ' + API_URL
  );
}

/**
 * API client class for backend communication.
 */
class APIClient {
  private baseURL: string;

  constructor(baseURL?: string) {
    this.baseURL = baseURL || API_URL || 'http://localhost:8000';
  }

  /**
   * Submit a company profile request to the backend.
   *
   * @param request - Company profile request data
   * @returns Profile request response with job ID
   * @throws Error if the request fails
   */
  async submitProfileRequest(
    request: CompanyProfileRequest
  ): Promise<ProfileRequestResponse> {
    try {
      const response = await axios.post<ProfileRequestResponse>(
        `${this.baseURL}/profile-request`,
        request,
        {
          headers: {
            'Content-Type': 'application/json',
          },
          timeout: 30000, // 30 second timeout
        }
      );

      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<ErrorResponse>;

        if (axiosError.response) {
          // Server responded with error
          const errorData = axiosError.response.data;
          throw new Error(
            errorData?.error ||
            errorData?.detail ||
            'Failed to submit profile request'
          );
        } else if (axiosError.request) {
          // Request made but no response
          throw new Error(
            'No response from server. Please check your connection.'
          );
        }
      }

      throw new Error('An unexpected error occurred');
    }
  }

  /**
   * Check the status of a job.
   *
   * @param jobId - Job ID to check
   * @returns Job status information
   * @throws Error if the request fails
   */
  async checkJobStatus(jobId: string): Promise<JobStatus> {
    try {
      const response = await axios.get<JobStatus>(
        `${this.baseURL}/job-status/${jobId}`,
        {
          timeout: 10000, // 10 second timeout
        }
      );

      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<ErrorResponse>;

        if (axiosError.response?.status === 404) {
          throw new Error('Job not found');
        }

        if (axiosError.response) {
          const errorData = axiosError.response.data;
          throw new Error(
            errorData?.error ||
            'Failed to check job status'
          );
        }
      }

      throw new Error('Failed to check job status');
    }
  }

  /**
   * Enrich contacts for a company domain via ZoomInfo Contact Enrich API.
   * Returns contacts with direct phone, mobile phone, company phone, and accuracy scores.
   * All phone data is attributed to ZoomInfo (phoneSource: 'zoominfo').
   *
   * This value must be provided via environment variables on the backend:
   *   ZOOMINFO_ACCESS_TOKEN or ZOOMINFO_CLIENT_ID + ZOOMINFO_CLIENT_SECRET
   *
   * @param domain - Company domain to enrich (e.g., 'example.com')
   * @returns ContactEnrichResponse with enriched contacts
   * @throws Error if enrichment fails or ZoomInfo is not configured
   */
  async enrichContacts(domain: string): Promise<ContactEnrichResponse> {
    try {
      const response = await axios.get<ContactEnrichResponse>(
        `${this.baseURL}/contacts/enrich/${encodeURIComponent(domain)}`,
        { timeout: 30000 }
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<ErrorResponse>;
        if (axiosError.response?.status === 503) {
          throw new Error('ZoomInfo not configured. ZOOMINFO_ACCESS_TOKEN must be provided via environment variables.');
        }
        if (axiosError.response) {
          const errorData = axiosError.response.data;
          throw new Error(errorData?.error || 'Contact enrichment failed');
        }
      }
      throw new Error('Failed to enrich contacts');
    }
  }

  /**
   * Check backend health.
   *
   * @returns True if backend is healthy, false otherwise
   */
  async checkHealth(): Promise<boolean> {
    try {
      const response = await axios.get(
        `${this.baseURL}/health`,
        { timeout: 5000 }
      );

      return response.status === 200;
    } catch {
      return false;
    }
  }
}

// Export singleton instance
export const apiClient = new APIClient();

// Export class for testing
export { APIClient };
