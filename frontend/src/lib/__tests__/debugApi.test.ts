/**
 * Tests for debug API client functions.
 * Features 018-021: Debug API integration
 * Following TDD - tests written first.
 */

import axios from 'axios';
import { debugApiClient } from '../debugApi';
import type { DebugData } from '@/types';

// Mock axios
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('debugApiClient', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('getDebugData', () => {
    const mockDebugData: DebugData = {
      jobId: 'job-123',
      companyName: 'Acme Corp',
      domain: 'acme.com',
      status: 'completed',
      processSteps: [
        {
          id: 'step-1',
          name: 'Data Collection',
          description: 'Gathering data from APIs',
          status: 'completed',
          startTime: '2024-01-15T10:00:00Z',
          endTime: '2024-01-15T10:00:05Z',
          duration: 5000,
        },
      ],
      apiResponses: [
        {
          id: 'api-1',
          apiName: 'Apollo.io',
          url: 'https://api.apollo.io/v1/companies',
          method: 'GET',
          statusCode: 200,
          statusText: 'OK',
          headers: {},
          responseBody: { company: {} },
          timestamp: '2024-01-15T10:00:00Z',
          duration: 245,
        },
      ],
      llmThoughtProcesses: [
        {
          id: 'llm-1',
          taskName: 'Data Validation',
          model: 'gpt-4',
          startTime: '2024-01-15T10:00:05Z',
          steps: [],
          finalDecision: 'Data validated successfully',
        },
      ],
      processFlow: {
        nodes: [
          {
            id: 'node-1',
            label: 'Start',
            type: 'start',
            status: 'completed',
          },
        ],
        edges: [],
      },
      createdAt: '2024-01-15T10:00:00Z',
      completedAt: '2024-01-15T10:00:30Z',
    };

    it('should fetch debug data successfully', async () => {
      mockedAxios.get.mockResolvedValueOnce({ data: mockDebugData });

      const result = await debugApiClient.getDebugData('job-123');

      expect(result).toEqual(mockDebugData);
      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.stringContaining('/debug-data/job-123'),
        expect.any(Object)
      );
    });

    it('should handle job not found error', async () => {
      mockedAxios.get.mockRejectedValueOnce({
        isAxiosError: true,
        response: {
          status: 404,
          data: { error: 'Job not found' },
        },
      });
      mockedAxios.isAxiosError = jest.fn().mockReturnValue(true);

      await expect(debugApiClient.getDebugData('invalid-job')).rejects.toThrow(
        'Debug data not found for job'
      );
    });

    it('should handle processing not complete error', async () => {
      mockedAxios.get.mockRejectedValueOnce({
        isAxiosError: true,
        response: {
          status: 400,
          data: { error: 'Processing not complete' },
        },
      });
      mockedAxios.isAxiosError = jest.fn().mockReturnValue(true);

      await expect(debugApiClient.getDebugData('job-123')).rejects.toThrow(
        'Processing not complete'
      );
    });

    it('should handle network errors', async () => {
      mockedAxios.get.mockRejectedValueOnce({
        isAxiosError: true,
        request: {},
      });
      mockedAxios.isAxiosError = jest.fn().mockReturnValue(true);

      await expect(debugApiClient.getDebugData('job-123')).rejects.toThrow(
        'No response from server'
      );
    });

    it('should handle unauthorized access', async () => {
      mockedAxios.get.mockRejectedValueOnce({
        isAxiosError: true,
        response: {
          status: 403,
          data: { error: 'Unauthorized' },
        },
      });
      mockedAxios.isAxiosError = jest.fn().mockReturnValue(true);

      await expect(debugApiClient.getDebugData('job-123')).rejects.toThrow(
        'Unauthorized access to debug data'
      );
    });
  });

  describe('getProcessSteps', () => {
    const mockProcessSteps = [
      {
        id: 'step-1',
        name: 'Data Collection',
        description: 'Gathering data',
        status: 'completed',
      },
    ];

    it('should fetch process steps successfully', async () => {
      mockedAxios.get.mockResolvedValueOnce({ data: mockProcessSteps });

      const result = await debugApiClient.getProcessSteps('job-123');

      expect(result).toEqual(mockProcessSteps);
      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.stringContaining('/debug-data/job-123/process-steps'),
        expect.any(Object)
      );
    });

    it('should handle errors', async () => {
      mockedAxios.get.mockRejectedValueOnce(new Error('Network error'));
      mockedAxios.isAxiosError = jest.fn().mockReturnValue(false);

      await expect(debugApiClient.getProcessSteps('job-123')).rejects.toThrow();
    });
  });

  describe('getAPIResponses', () => {
    const mockAPIResponses = [
      {
        id: 'api-1',
        apiName: 'Apollo.io',
        url: 'https://api.apollo.io',
        method: 'GET',
        statusCode: 200,
        statusText: 'OK',
        headers: {},
        responseBody: {},
        timestamp: '2024-01-15T10:00:00Z',
        duration: 245,
      },
    ];

    it('should fetch API responses successfully', async () => {
      mockedAxios.get.mockResolvedValueOnce({ data: mockAPIResponses });

      const result = await debugApiClient.getAPIResponses('job-123');

      expect(result).toEqual(mockAPIResponses);
      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.stringContaining('/debug-data/job-123/api-responses'),
        expect.any(Object)
      );
    });

    it('should apply sensitive data masking by default', async () => {
      mockedAxios.get.mockResolvedValueOnce({ data: mockAPIResponses });

      await debugApiClient.getAPIResponses('job-123');

      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          params: expect.objectContaining({
            mask_sensitive: true,
          }),
        })
      );
    });

    it('should allow disabling sensitive data masking', async () => {
      mockedAxios.get.mockResolvedValueOnce({ data: mockAPIResponses });

      await debugApiClient.getAPIResponses('job-123', { maskSensitive: false });

      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          params: expect.objectContaining({
            mask_sensitive: false,
          }),
        })
      );
    });
  });

  describe('getLLMThoughtProcesses', () => {
    const mockLLMProcesses = [
      {
        id: 'llm-1',
        taskName: 'Validation',
        model: 'gpt-4',
        startTime: '2024-01-15T10:00:00Z',
        steps: [],
        finalDecision: 'Validated',
      },
    ];

    it('should fetch LLM thought processes successfully', async () => {
      mockedAxios.get.mockResolvedValueOnce({ data: mockLLMProcesses });

      const result = await debugApiClient.getLLMThoughtProcesses('job-123');

      expect(result).toEqual(mockLLMProcesses);
      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.stringContaining('/debug-data/job-123/llm-processes'),
        expect.any(Object)
      );
    });
  });

  describe('getProcessFlow', () => {
    const mockProcessFlow = {
      nodes: [
        { id: 'node-1', label: 'Start', type: 'start', status: 'completed' },
      ],
      edges: [],
    };

    it('should fetch process flow successfully', async () => {
      mockedAxios.get.mockResolvedValueOnce({ data: mockProcessFlow });

      const result = await debugApiClient.getProcessFlow('job-123');

      expect(result).toEqual(mockProcessFlow);
      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.stringContaining('/debug-data/job-123/process-flow'),
        expect.any(Object)
      );
    });
  });

  describe('checkDebugAvailable', () => {
    it('should return true when debug data is available', async () => {
      mockedAxios.head.mockResolvedValueOnce({ status: 200 });

      const result = await debugApiClient.checkDebugAvailable('job-123');

      expect(result).toBe(true);
    });

    it('should return false when debug data is not available', async () => {
      mockedAxios.head.mockRejectedValueOnce({ response: { status: 404 } });

      const result = await debugApiClient.checkDebugAvailable('job-123');

      expect(result).toBe(false);
    });
  });
});
