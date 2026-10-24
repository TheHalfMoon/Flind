import * as AuthSession from "expo-auth-session";
import * as WebBrowser from "expo-web-browser";
import { getFlindStudioApiHost, getFlindStudioOAuthClientId } from "@/config";

WebBrowser.maybeCompleteAuthSession();

export type CloudRegion = "us" | "eu";

const SCOPES = [
  "user:read",
  "user:write",
  "project:read",
  "organization:read",
  "organization:write",
  "task:write",
  "integration:read",
  "conversation:write",
  "insight:read",
  "query:read",
  "llm_skill:read",
];

export const OAUTH_SCOPE_VERSION = 1;

export interface OAuthTokens {
  access_token: string;
  expires_in: number;
  refresh_token: string;
  scoped_teams?: number[];
}

function redirectUri(): string {
  return AuthSession.makeRedirectUri({ scheme: "flind-studio", path: "callback" });
}

async function tokenRequest(
  region: CloudRegion,
  body: Record<string, string>,
): Promise<OAuthTokens> {
  const response = await fetch(`${getFlindStudioApiHost(region)}/oauth/token`, {
    method: "POST",
    redirect: "error",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...body, client_id: getFlindStudioOAuthClientId(region) }),
  });
  if (!response.ok) {
    throw new Error(
      `Token request failed (${response.status}): ${await response.text()}`,
    );
  }
  return (await response.json()) as OAuthTokens;
}

export interface SignInOptions {
  // Open account creation first; the browser lands on the authorize page
  // afterwards, so a new user ends up signed in to the app.
  signup?: boolean;
}

export async function signInWithOAuth(
  region: CloudRegion,
  { signup = false }: SignInOptions = {},
): Promise<OAuthTokens> {
  const host = getFlindStudioApiHost(region);
  const request = new AuthSession.AuthRequest({
    clientId: getFlindStudioOAuthClientId(region),
    scopes: SCOPES,
    redirectUri: redirectUri(),
    usePKCE: true,
    extraParams: { required_access_level: "project" },
  });
  const discovery = { authorizationEndpoint: `${host}/oauth/authorize` };
  const authUrl = await request.makeAuthUrlAsync(discovery);
  const next = encodeURIComponent(authUrl.slice(host.length));
  const result = await request.promptAsync(discovery, {
    url: signup ? `${host}/signup?next=${next}` : authUrl,
    // Let users choose an account without reusing Safari's signed-in account.
    preferEphemeralSession: true,
  });
  if (result.type !== "success" || !result.params.code) {
    throw new Error(
      result.type === "error"
        ? (result.error?.message ?? "Authorization failed")
        : "Sign in was cancelled",
    );
  }
  if (!request.codeVerifier) throw new Error("PKCE verifier missing");
  return tokenRequest(region, {
    grant_type: "authorization_code",
    code: result.params.code,
    redirect_uri: redirectUri(),
    code_verifier: request.codeVerifier,
  });
}

export function refreshOAuth(
  region: CloudRegion,
  refreshToken: string,
): Promise<OAuthTokens> {
  return tokenRequest(region, {
    grant_type: "refresh_token",
    refresh_token: refreshToken,
  });
}
