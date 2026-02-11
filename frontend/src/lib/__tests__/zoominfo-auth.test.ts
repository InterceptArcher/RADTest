/**
 * Tests for ZoomInfo OAuth authentication helper.
 * TDD: Tests written FIRST before implementation.
 */

import { buildZoomInfoLoginUrl, exchangeCodeForTokens } from '../zoominfo-auth';

// Mock fetch globally
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('ZoomInfo Auth Utilities', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('buildZoomInfoLoginUrl', () => {
    it('should build a valid login URL with all required parameters', () => {
      const params = {
        clientId: 'test-client-id',
        redirectUri: 'https://example.com/api/auth/zoominfo/callback',
        state: 'test-state-uuid',
        codeChallenge: 'test-code-challenge',
      };

      const url = buildZoomInfoLoginUrl(params);
      const parsed = new URL(url);

      expect(parsed.origin).toBe('https://login.zoominfo.com');
      expect(parsed.searchParams.get('client_id')).toBe('test-client-id');
      expect(parsed.searchParams.get('redirect_uri')).toBe(
        'https://example.com/api/auth/zoominfo/callback'
      );
      expect(parsed.searchParams.get('state')).toBe('test-state-uuid');
      expect(parsed.searchParams.get('code_challenge')).toBe('test-code-challenge');
      expect(parsed.searchParams.get('response_type')).toBe('code');
      expect(parsed.searchParams.get('code_challenge_method')).toBe('S256');
      expect(parsed.searchParams.get('scope')).toBe('openid');
    });

    it('should include custom scopes when provided', () => {
      const params = {
        clientId: 'test-client-id',
        redirectUri: 'https://example.com/api/auth/zoominfo/callback',
        state: 'test-state-uuid',
        codeChallenge: 'test-code-challenge',
        scopes: 'openid ziapi',
      };

      const url = buildZoomInfoLoginUrl(params);
      const parsed = new URL(url);

      expect(parsed.searchParams.get('scope')).toBe('openid ziapi');
    });
  });

  describe('exchangeCodeForTokens', () => {
    const exchangeParams = {
      code: 'auth-code-123',
      redirectUri: 'https://example.com/api/auth/zoominfo/callback',
      codeVerifier: 'test-code-verifier',
      clientId: 'test-client-id',
      clientSecret: 'test-client-secret',
    };

    it('should exchange an authorization code for tokens', async () => {
      const mockTokenResponse = {
        access_token: 'access-token-xyz',
        id_token: 'id-token-xyz',
        refresh_token: 'refresh-token-xyz',
        token_type: 'Bearer',
        expires_in: 86400,
        scope: 'openid',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTokenResponse,
      });

      const result = await exchangeCodeForTokens(exchangeParams);

      expect(result.access_token).toBe('access-token-xyz');
      expect(result.refresh_token).toBe('refresh-token-xyz');
      expect(result.token_type).toBe('Bearer');
      expect(result.expires_in).toBe(86400);
    });

    it('should send the correct request to the Okta token endpoint', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          access_token: 'token',
          token_type: 'Bearer',
          expires_in: 86400,
        }),
      });

      await exchangeCodeForTokens(exchangeParams);

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url, options] = mockFetch.mock.calls[0];

      expect(url).toBe('https://okta-login.zoominfo.com/oauth2/default/v1/token');
      expect(options.method).toBe('POST');

      // Check Authorization header is Basic auth with base64(clientId:clientSecret)
      const expectedAuth = Buffer.from('test-client-id:test-client-secret').toString('base64');
      expect(options.headers['Authorization']).toBe(`Basic ${expectedAuth}`);
      expect(options.headers['Content-Type']).toBe('application/x-www-form-urlencoded');

      // Check body parameters
      const body = new URLSearchParams(options.body);
      expect(body.get('code')).toBe('auth-code-123');
      expect(body.get('grant_type')).toBe('authorization_code');
      expect(body.get('redirect_uri')).toBe(
        'https://example.com/api/auth/zoominfo/callback'
      );
      expect(body.get('code_verifier')).toBe('test-code-verifier');
    });

    it('should throw an error when token exchange fails', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        text: async () => 'Invalid authorization code',
      });

      await expect(exchangeCodeForTokens(exchangeParams)).rejects.toThrow(
        'Token exchange failed'
      );
    });

    it('should throw an error on network failure', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(exchangeCodeForTokens(exchangeParams)).rejects.toThrow('Network error');
    });
  });
});
