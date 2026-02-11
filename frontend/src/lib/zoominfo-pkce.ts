/**
 * ZoomInfo PKCE (Proof Key for Code Exchange) utilities.
 *
 * Implements the OAuth 2.0 PKCE extension required by ZoomInfo's Okta-based
 * authentication. Generates code verifiers, code challenges, and state tokens.
 */

import crypto from 'crypto';

/**
 * Generate a cryptographically random code verifier.
 * Creates a 32-byte random string, Base64-encodes it, then applies
 * URL-safe transformations per the PKCE spec.
 */
export function generateCodeVerifier(): string {
  const buffer = crypto.randomBytes(32);
  return buffer
    .toString('base64')
    .replace(/\//g, '_')
    .replace(/\+/g, '-')
    .replace(/=/g, '');
}

/**
 * Generate a code challenge from a code verifier using SHA-256.
 * Hashes the verifier, Base64-encodes the result, then applies
 * URL-safe transformations.
 */
export async function generateCodeChallenge(verifier: string): Promise<string> {
  const hash = crypto.createHash('sha256').update(verifier).digest('base64');
  return hash
    .replace(/\//g, '_')
    .replace(/\+/g, '-')
    .replace(/=/g, '');
}

/**
 * Generate a random UUID v4 state parameter for OAuth request-callback correlation.
 */
export function generateState(): string {
  return crypto.randomUUID();
}
