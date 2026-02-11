/**
 * GET /api/auth/zoominfo/callback
 *
 * Handles the OAuth 2.0 callback redirect from ZoomInfo.
 * Receives the authorization code and state, validates the state against the
 * stored cookie, exchanges the code for tokens using PKCE, and redirects
 * the user to the dashboard with the session established.
 *
 * This is the "Sign-in redirect URI" that must be registered in the
 * ZoomInfo Developer Portal when creating your app.
 */

import { NextRequest, NextResponse } from 'next/server';
import { exchangeCodeForTokens } from '@/lib/zoominfo-auth';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const code = searchParams.get('code');
  const state = searchParams.get('state');
  const error = searchParams.get('error');
  const errorDescription = searchParams.get('error_description');

  // Handle errors returned by ZoomInfo/Okta
  if (error) {
    console.error(`ZoomInfo OAuth error: ${error} - ${errorDescription}`);
    return NextResponse.redirect(
      new URL(`/auth/error?error=${encodeURIComponent(error)}&description=${encodeURIComponent(errorDescription || '')}`, request.url)
    );
  }

  // Validate required parameters
  if (!code || !state) {
    console.error('ZoomInfo callback missing code or state parameter');
    return NextResponse.redirect(
      new URL('/auth/error?error=missing_params&description=Authorization+code+or+state+missing', request.url)
    );
  }

  // Retrieve stored PKCE values from cookies
  const storedState = request.cookies.get('zi_oauth_state')?.value;
  const codeVerifier = request.cookies.get('zi_code_verifier')?.value;

  // Validate state to prevent CSRF attacks
  if (!storedState || state !== storedState) {
    console.error('ZoomInfo callback state mismatch — possible CSRF attack');
    return NextResponse.redirect(
      new URL('/auth/error?error=state_mismatch&description=Invalid+state+parameter', request.url)
    );
  }

  if (!codeVerifier) {
    console.error('ZoomInfo callback missing code verifier cookie');
    return NextResponse.redirect(
      new URL('/auth/error?error=missing_verifier&description=PKCE+code+verifier+not+found', request.url)
    );
  }

  // Validate environment configuration
  const clientId = process.env.ZOOMINFO_CLIENT_ID;
  const clientSecret = process.env.ZOOMINFO_CLIENT_SECRET;

  if (!clientId || !clientSecret) {
    console.error('ZoomInfo client credentials not configured');
    return NextResponse.redirect(
      new URL('/auth/error?error=server_config&description=Server+configuration+error', request.url)
    );
  }

  const redirectUri = `${request.nextUrl.origin}/api/auth/zoominfo/callback`;

  try {
    // Exchange authorization code for tokens
    const tokens = await exchangeCodeForTokens({
      code,
      redirectUri,
      codeVerifier,
      clientId,
      clientSecret,
    });

    // Build redirect response to the dashboard
    const dashboardUrl = new URL('/dashboard', request.url);
    const response = NextResponse.redirect(dashboardUrl);

    // Store access token in HTTP-only secure cookie
    response.cookies.set('zi_access_token', tokens.access_token, {
      httpOnly: true,
      secure: true,
      sameSite: 'lax',
      path: '/',
      maxAge: tokens.expires_in, // Typically 86400 (24 hours)
    });

    // Store refresh token if provided
    if (tokens.refresh_token) {
      response.cookies.set('zi_refresh_token', tokens.refresh_token, {
        httpOnly: true,
        secure: true,
        sameSite: 'lax',
        path: '/api/auth',
        maxAge: 30 * 24 * 60 * 60, // 30 days
      });
    }

    // Store token type and expiry for client-side awareness (non-sensitive)
    response.cookies.set('zi_authenticated', 'true', {
      httpOnly: false,
      secure: true,
      sameSite: 'lax',
      path: '/',
      maxAge: tokens.expires_in,
    });

    // Clear the PKCE cookies — they are single-use
    response.cookies.delete('zi_code_verifier');
    response.cookies.delete('zi_oauth_state');

    console.log('ZoomInfo OAuth callback: tokens exchanged successfully');
    return response;
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error during token exchange';
    console.error(`ZoomInfo token exchange failed: ${message}`);
    return NextResponse.redirect(
      new URL(`/auth/error?error=token_exchange&description=${encodeURIComponent(message)}`, request.url)
    );
  }
}
