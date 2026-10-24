import type { CloudRegion } from "../types";

export const OAUTH_SCOPES = [
  "user:read",
  // Required for POST /api/users/@me/push_tokens/ — without it the backend
  // rejects push-token registration with 403 and notifications never fire.
  "user:write",
  "project:read",
  // Required for the organization consent gate: the beta-terms read and the
  // AI-data-processing / beta-terms writes hit organization-scoped endpoints.
  "organization:read",
  "organization:write",
  "task:write",
  "integration:read",
  "conversation:write",
  "query:read",
  "llm_skill:read",
];

export const OAUTH_SCOPE_VERSION = 2;

// Token refresh settings
export const TOKEN_REFRESH_BUFFER_MS = 5 * 60 * 1000; // 5 minutes before expiry

/**
 * Flind mobile must never inherit an upstream SaaS URL, OAuth client ID, or
 * insecure external origin. Expo statically substitutes the literal
 * EXPO_PUBLIC_... lookups at bundle build time.
 */
function validatedApiOrigin(raw: string | undefined, region: CloudRegion): string {
  if (!raw || raw.trim() !== raw) {
    throw new Error(`Flind mobile API URL for ${region} is not configured`);
  }

  let parsed: URL;
  try {
    parsed = new URL(raw);
  } catch {
    throw new Error(`Flind mobile API URL for ${region} must be an absolute origin`);
  }

  const hostname = parsed.hostname.toLowerCase().replace(/\.+$/, "");
  const inheritedHost = hostname === "posthog.com" || hostname.endsWith(".posthog.com");
  const local = hostname === "localhost" || hostname.endsWith(".localhost")
    || hostname === "127.0.0.1" || hostname === "[::1]";
  if (inheritedHost || (parsed.protocol !== "https:" && !(parsed.protocol === "http:" && local))) {
    throw new Error(`Flind mobile API URL for ${region} is not an approved destination`);
  }
  if (
    !parsed.hostname ||
    parsed.username ||
    parsed.password ||
    parsed.pathname !== "/" ||
    parsed.search ||
    parsed.hash
  ) {
    throw new Error(`Flind mobile API URL for ${region} must be an origin without credentials or extra paths`);
  }
  return parsed.origin;
}

export function getCloudUrlFromRegion(region: CloudRegion): string {
  switch (region) {
    case "us":
      return validatedApiOrigin(process.env.EXPO_PUBLIC_FLIND_API_US_URL, region);
    case "eu":
      return validatedApiOrigin(process.env.EXPO_PUBLIC_FLIND_API_EU_URL, region);
    case "dev":
      return validatedApiOrigin(process.env.EXPO_PUBLIC_FLIND_API_DEV_URL ?? "http://localhost:8010", region);
    default:
      throw new Error("Unknown Flind mobile region");
  }
}

export function getOauthClientIdFromRegion(region: CloudRegion): string {
  let id: string | undefined;
  switch (region) {
    case "us":
      id = process.env.EXPO_PUBLIC_FLIND_OAUTH_US_CLIENT_ID;
      break;
    case "eu":
      id = process.env.EXPO_PUBLIC_FLIND_OAUTH_EU_CLIENT_ID;
      break;
    case "dev":
      id = process.env.EXPO_PUBLIC_FLIND_OAUTH_DEV_CLIENT_ID;
      break;
    default:
      throw new Error("Unknown Flind mobile region");
  }
  if (!id || !/^[a-zA-Z0-9_-]+$/.test(id)) {
    throw new Error(`Flind mobile OAuth client ID for ${region} is not configured`);
  }
  return id;
}
