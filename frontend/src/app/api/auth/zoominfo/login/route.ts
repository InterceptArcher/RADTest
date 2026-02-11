/**
 * GET /api/auth/zoominfo/login
 *
 * Initiates the ZoomInfo OAuth 2.0 + PKCE sign-in flow.
 * Generates a code verifier/challenge pair and state token, stores the verifier
 * and state in HTTP-only cookies, and redirects the user to ZoomInfo's login page.
 */

import { NextResponse } from 'next/server';
import { generateCodeVerifier, generateCodeChallenge, generateState } from '@/lib/zoominfo-pkce';
import { buildZoomInfoLoginUrl } from '@/lib/zoominfo-auth';

export async function GET(request: Request) {
  const clientId = process.env.ZOOMINFO_CLIENT_ID;

  if (!clientId) {
    return NextResponse.json(
      { error: 'ZOOMINFO_CLIENT_ID is not configured' },
      { status: 500 }
    );
  }

  // Determine the callback URL from the request origin
  const url = new URL(request.url);
  const redirectUri = `${url.origin}/api/auth/zoominfo/callback`;

  // Generate PKCE values
  const state = generateState();
  const codeVerifier = generateCodeVerifier();
  const codeChallenge = await generateCodeChallenge(codeVerifier);

  // Build the ZoomInfo login URL
  const loginUrl = buildZoomInfoLoginUrl({
    clientId,
    redirectUri,
    state,
    codeChallenge,
    scopes: process.env.ZOOMINFO_SCOPES || 'openid',
  });

  // Store PKCE verifier and state in HTTP-only cookies for retrieval during callback
  const response = NextResponse.redirect(loginUrl);

  response.cookies.set('zi_code_verifier', codeVerifier, {
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    path: '/api/auth/zoominfo/callback',
    maxAge: 600, // 10 minutes — enough time to complete the login
  });

  response.cookies.set('zi_oauth_state', state, {
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    path: '/api/auth/zoominfo/callback',
    maxAge: 600,
  });

  return response;
}
