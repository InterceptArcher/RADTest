/**
 * Tests for API client.
 * Following TDD - tests written to verify API communication.
 */

import axios from 'axios';
import { APIClient } from '../api';
import type { CompanyProfileRequest } from '@/types';

// Mock axios
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('APIClient', () => {
  let client: APIClient;

  beforeEach(() => {
    client = new APIClient('http://localhost:8000');
    jest.clearAllMocks();
  });

  describe('submitProfileRequest', () => {
    const validRequest: CompanyProfileRequest = {
      company_name: 'Acme Corp',
      domain: 'acme.com',
      industry: 'Technology',
      requested_by: 'user@example.com',
    };

    it('should submit profile request successfully', async () => {
      const mockResponse = {
        data: {
          status: 'success',
          job_id: 'job-123',
          message: 'Request submitted',
        },
      };

      mockedAxios.post.mockResolvedValueOnce(mockResponse);

      const result = await client.submitProfileRequest(validRequest);

      expect(result.status).toBe('success');
      expect(result.job_id).toBe('job-123');
      expect(mockedAxios.post).toHaveBeenCalledWith(
        'http://localhost:8000/profile-request',
        validRequest,
        expect.objectContaining({
          headers: { 'Content-Type': 'application/json' },
        })
      );
    });

    it('should handle server error responses', async () => {
      mockedAxios.post.mockRejectedValueOnce({
        isAxiosError: true,
        response: {
          data: {
            error: 'Server error',
          },
        },
      });

      mockedAxios.isAxiosError = jest.fn().mockReturnValue(true);

      await expect(
        client.submitProfileRequest(validRequest)
      ).rejects.toThrow('Server error');
    });

    it('should handle network errors', async () => {
      mockedAxios.post.mockRejectedValueOnce({
        isAxiosError: true,
        request: {},
      });

      mockedAxios.isAxiosError = jest.fn().mockReturnValue(true);

      await expect(
        client.submitProfileRequest(validRequest)
      ).rejects.toThrow('No response from server');
    });

    it('should handle unexpected errors', async () => {
      mockedAxios.post.mockRejectedValueOnce(new Error('Unexpected'));

      mockedAxios.isAxiosError = jest.fn().mockReturnValue(false);

      await expect(
        client.submitProfileRequest(validRequest)
      ).rejects.toThrow('An unexpected error occurred');
    });
  });

  describe('checkJobStatus', () => {
    it('should check job status successfully', async () => {
      const mockResponse = {
        data: {
          job_id: 'job-123',
          status: 'completed',
          result: {
            success: true,
            company_name: 'Acme Corp',
            domain: 'acme.com',
            slideshow_url: 'https://example.com/slideshow',
            confidence_score: 0.85,
          },
        },
      };

      mockedAxios.get.mockResolvedValueOnce(mockResponse);

      const result = await client.checkJobStatus('job-123');

      expect(result.job_id).toBe('job-123');
      expect(result.status).toBe('completed');
      expect(mockedAxios.get).toHaveBeenCalledWith(
        'http://localhost:8000/job-status/job-123',
        expect.any(Object)
      );
    });

    it('should handle job not found', async () => {
      mockedAxios.get.mockRejectedValueOnce({
        isAxiosError: true,
        response: {
          status: 404,
        },
      });

      mockedAxios.isAxiosError = jest.fn().mockReturnValue(true);

      await expect(client.checkJobStatus('invalid-job')).rejects.toThrow(
        'Job not found'
      );
    });

    it('should handle server errors', async () => {
      mockedAxios.get.mockRejectedValueOnce({
        isAxiosError: true,
        response: {
          data: {
            error: 'Internal server error',
          },
        },
      });

      mockedAxios.isAxiosError = jest.fn().mockReturnValue(true);

      await expect(client.checkJobStatus('job-123')).rejects.toThrow();
    });
  });

  describe('checkHealth', () => {
    it('should return true for healthy backend', async () => {
      mockedAxios.get.mockResolvedValueOnce({ status: 200 });

      const result = await client.checkHealth();

      expect(result).toBe(true);
      expect(mockedAxios.get).toHaveBeenCalledWith(
        'http://localhost:8000/health',
        expect.any(Object)
      );
    });

    it('should return false for unhealthy backend', async () => {
      mockedAxios.get.mockRejectedValueOnce(new Error('Connection failed'));

      const result = await client.checkHealth();

      expect(result).toBe(false);
    });
  });
});
