/**
 * ZoomInfo OAuth 2.0 authentication helper.
 *
 * Provides utilities for building the ZoomInfo login URL and exchanging
 * authorization codes for tokens via ZoomInfo's Okta token endpoint.
 */

const ZOOMINFO_LOGIN_URL = 'https://login.zoominfo.com';
const ZOOMINFO_TOKEN_URL = 'https://okta-login.zoominfo.com/oauth2/default/v1/token';

interface LoginUrlParams {
  clientId: string;
  redirectUri: string;
  state: string;
  codeChallenge: string;
  scopes?: string;
}

interface TokenExchangeParams {
  code: string;
  redirectUri: string;
  codeVerifier: string;
  clientId: string;
  clientSecret: string;
}

export interface ZoomInfoTokenResponse {
  access_token: string;
  id_token?: string;
  refresh_token?: string;
  token_type: string;
  expires_in: number;
  scope?: string;
}

/**
 * Build the ZoomInfo login URL with all required OAuth/PKCE query parameters.
 */
export function buildZoomInfoLoginUrl(params: LoginUrlParams): string {
  const url = new URL(ZOOMINFO_LOGIN_URL);

  url.searchParams.set('client_id', params.clientId);
  url.searchParams.set('redirect_uri', params.redirectUri);
  url.searchParams.set('state', params.state);
  url.searchParams.set('code_challenge', params.codeChallenge);
  url.searchParams.set('code_challenge_method', 'S256');
  url.searchParams.set('response_type', 'code');
  url.searchParams.set('scope', params.scopes || 'openid');

  return url.toString();
}

/**
 * Exchange an authorization code for access/refresh tokens at ZoomInfo's Okta endpoint.
 * Uses Basic authentication with the client credentials and includes the PKCE code verifier.
 */
export async function exchangeCodeForTokens(
  params: TokenExchangeParams
): Promise<ZoomInfoTokenResponse> {
  const basicAuth = Buffer.from(`${params.clientId}:${params.clientSecret}`).toString('base64');

  const body = new URLSearchParams({
    code: params.code,
    grant_type: 'authorization_code',
    redirect_uri: params.redirectUri,
    code_verifier: params.codeVerifier,
  });

  const response = await fetch(ZOOMINFO_TOKEN_URL, {
    method: 'POST',
    headers: {
      'Authorization': `Basic ${basicAuth}`,
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: body.toString(),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Token exchange failed: ${response.status} ${response.statusText} - ${errorText}`);
  }

  return response.json();
}
