/**
 * Debug API client for fetching debug data.
 * Features 018-021: Debug API Integration
 *
 * IMPORTANT: Backend API URL must be provided via NEXT_PUBLIC_API_URL
 * environment variable. Never hardcode URLs or secrets.
 */

import axios, { AxiosError } from 'axios';
import type {
  DebugData,
  ProcessStep,
  APIResponseData,
  LLMThoughtProcess,
  ProcessFlow,
} from '@/types';

// Get API URL from environment variable, with fallback to production Render URL
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://radtest-backend.onrender.com';

interface ErrorResponse {
  error: string;
  detail?: string;
}

interface GetAPIResponsesOptions {
  maskSensitive?: boolean;
}

/**
 * Debug API client class for fetching debug information.
 */
class DebugAPIClient {
  private baseURL: string;

  constructor(baseURL?: string) {
    this.baseURL = baseURL || API_URL || 'http://localhost:8000';
  }

  /**
   * Get complete debug data for a job.
   *
   * @param jobId - Job ID to fetch debug data for
   * @returns Complete debug data
   * @throws Error if the request fails
   */
  async getDebugData(jobId: string): Promise<DebugData> {
    try {
      const response = await axios.get<DebugData>(
        `${this.baseURL}/debug-data/${jobId}`,
        {
          timeout: 30000,
        }
      );

      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<ErrorResponse>;

        if (axiosError.response?.status === 404) {
          throw new Error('Debug data not found for job');
        }

        if (axiosError.response?.status === 403) {
          throw new Error('Unauthorized access to debug data');
        }

        if (axiosError.response?.status === 400) {
          throw new Error(
            axiosError.response.data?.error || 'Processing not complete'
          );
        }

        if (axiosError.request && !axiosError.response) {
          throw new Error('No response from server');
        }

        throw new Error(
          axiosError.response?.data?.error || 'Failed to fetch debug data'
        );
      }

      throw new Error('An unexpected error occurred');
    }
  }

  /**
   * Get process steps for a job.
   *
   * @param jobId - Job ID to fetch process steps for
   * @returns Array of process steps
   * @throws Error if the request fails
   */
  async getProcessSteps(jobId: string): Promise<ProcessStep[]> {
    try {
      const response = await axios.get<ProcessStep[]>(
        `${this.baseURL}/debug-data/${jobId}/process-steps`,
        {
          timeout: 15000,
        }
      );

      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<ErrorResponse>;
        throw new Error(
          axiosError.response?.data?.error || 'Failed to fetch process steps'
        );
      }
      throw error;
    }
  }

  /**
   * Get API responses for a job.
   *
   * @param jobId - Job ID to fetch API responses for
   * @param options - Options including maskSensitive flag
   * @returns Array of API response data
   * @throws Error if the request fails
   */
  async getAPIResponses(
    jobId: string,
    options: GetAPIResponsesOptions = {}
  ): Promise<APIResponseData[]> {
    const { maskSensitive = true } = options;

    try {
      const response = await axios.get<APIResponseData[]>(
        `${this.baseURL}/debug-data/${jobId}/api-responses`,
        {
          timeout: 15000,
          params: {
            mask_sensitive: maskSensitive,
          },
        }
      );

      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<ErrorResponse>;
        throw new Error(
          axiosError.response?.data?.error || 'Failed to fetch API responses'
        );
      }
      throw error;
    }
  }

  /**
   * Get LLM thought processes for a job.
   *
   * @param jobId - Job ID to fetch LLM thought processes for
   * @returns Array of LLM thought processes
   * @throws Error if the request fails
   */
  async getLLMThoughtProcesses(jobId: string): Promise<LLMThoughtProcess[]> {
    try {
      const response = await axios.get<LLMThoughtProcess[]>(
        `${this.baseURL}/debug-data/${jobId}/llm-processes`,
        {
          timeout: 15000,
        }
      );

      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<ErrorResponse>;
        throw new Error(
          axiosError.response?.data?.error ||
            'Failed to fetch LLM thought processes'
        );
      }
      throw error;
    }
  }

  /**
   * Get process flow for a job.
   *
   * @param jobId - Job ID to fetch process flow for
   * @returns Process flow data
   * @throws Error if the request fails
   */
  async getProcessFlow(jobId: string): Promise<ProcessFlow> {
    try {
      const response = await axios.get<ProcessFlow>(
        `${this.baseURL}/debug-data/${jobId}/process-flow`,
        {
          timeout: 15000,
        }
      );

      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<ErrorResponse>;
        throw new Error(
          axiosError.response?.data?.error || 'Failed to fetch process flow'
        );
      }
      throw error;
    }
  }

  /**
   * Check if debug data is available for a job.
   *
   * @param jobId - Job ID to check
   * @returns True if debug data is available
   */
  async checkDebugAvailable(jobId: string): Promise<boolean> {
    try {
      await axios.head(`${this.baseURL}/debug-data/${jobId}`, {
        timeout: 5000,
      });
      return true;
    } catch {
      return false;
    }
  }
}

// Export singleton instance
export const debugApiClient = new DebugAPIClient();

// Export class for testing
export { DebugAPIClient };
