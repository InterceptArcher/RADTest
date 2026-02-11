/**
 * Tests for ZoomInfo PKCE utility functions.
 * TDD: Tests written FIRST before implementation.
 */

import { generateCodeVerifier, generateCodeChallenge, generateState } from '../zoominfo-pkce';

describe('ZoomInfo PKCE Utilities', () => {
  describe('generateCodeVerifier', () => {
    it('should generate a URL-safe base64 string', () => {
      const verifier = generateCodeVerifier();

      // Must not contain characters that are not URL-safe
      expect(verifier).not.toMatch(/[+/=]/);
      // Must only contain URL-safe base64 characters
      expect(verifier).toMatch(/^[A-Za-z0-9_-]+$/);
    });

    it('should generate a string of appropriate length', () => {
      const verifier = generateCodeVerifier();

      // 32 bytes base64-encoded = ~43 chars (before padding removal)
      expect(verifier.length).toBeGreaterThanOrEqual(32);
      expect(verifier.length).toBeLessThanOrEqual(128);
    });

    it('should generate unique values on each call', () => {
      const verifier1 = generateCodeVerifier();
      const verifier2 = generateCodeVerifier();

      expect(verifier1).not.toBe(verifier2);
    });
  });

  describe('generateCodeChallenge', () => {
    it('should generate a URL-safe base64 string from a verifier', async () => {
      const verifier = generateCodeVerifier();
      const challenge = await generateCodeChallenge(verifier);

      // Must not contain characters that are not URL-safe
      expect(challenge).not.toMatch(/[+/=]/);
      // Must only contain URL-safe base64 characters
      expect(challenge).toMatch(/^[A-Za-z0-9_-]+$/);
    });

    it('should produce a consistent challenge for the same verifier', async () => {
      const verifier = 'test-verifier-value-for-consistency';
      const challenge1 = await generateCodeChallenge(verifier);
      const challenge2 = await generateCodeChallenge(verifier);

      expect(challenge1).toBe(challenge2);
    });

    it('should produce different challenges for different verifiers', async () => {
      const challenge1 = await generateCodeChallenge('verifier-one');
      const challenge2 = await generateCodeChallenge('verifier-two');

      expect(challenge1).not.toBe(challenge2);
    });

    it('should produce a SHA-256 hash (43 chars URL-safe base64)', async () => {
      const verifier = generateCodeVerifier();
      const challenge = await generateCodeChallenge(verifier);

      // SHA-256 produces 32 bytes = 43 base64 chars without padding
      expect(challenge.length).toBe(43);
    });
  });

  describe('generateState', () => {
    it('should generate a UUID-format string', () => {
      const state = generateState();

      // UUID v4 format: 8-4-4-4-12 hex chars
      expect(state).toMatch(
        /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/
      );
    });

    it('should generate unique values on each call', () => {
      const state1 = generateState();
      const state2 = generateState();

      expect(state1).not.toBe(state2);
    });
  });
});
