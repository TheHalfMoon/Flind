// Local stack by default. Use your LAN IP instead of localhost on a real phone.
export const FLIND_LOCAL_HOST = "http://localhost:8010";

// Prefilled on the login screen in development builds only.
export const DEV_EMAIL = "test@posthog.com";
export const DEV_PASSWORD = "12345678";

// "owner/repo". Null uses the most recently used repository on the project.
export const DEFAULT_REPOSITORY: string | null = null;

export const DEFAULT_MODEL = "claude-opus-4-8";

/** Explicit Flind Mobile Studio origins; never inherit upstream SaaS URLs. */
export type StudioRegion = "local" | "us" | "eu";

function validateStudioUrl(raw: string | undefined, purpose: string, path: string): string {
  if (!raw || raw.trim() !== raw) {
    throw new Error("Flind Mobile Studio " + purpose + " URL is not configured");
  }
  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    throw new Error("Flind Mobile Studio " + purpose + " URL must be absolute");
  }
  const host = url.hostname.toLowerCase().replace(/\.+$/, "");
  const loopback = host === "localhost" || host.endsWith(".localhost")
    || host === "127.0.0.1" || host === "[::1]";
  const inherited = host === "posthog.com" || host.endsWith(".posthog.com");
  if (!host || inherited || (url.protocol !== "https:" && !(url.protocol === "http:" && loopback))) {
    throw new Error("Flind Mobile Studio " + purpose + " URL is not an approved destination");
  }
  const validPath = path === "/" ? url.pathname === "/" : (url.pathname === path || url.pathname === path + "/");
  if (!validPath || url.username || url.password || url.search || url.hash) {
    throw new Error("Flind Mobile Studio " + purpose + " URL contains unsupported URL components");
  }
  return path === "/" ? url.origin : url.origin + path;
}

export function getFlindStudioApiHost(region: "us" | "eu"): string {
  switch (region) {
    case "us":
      return validateStudioUrl(process.env.EXPO_PUBLIC_FLIND_STUDIO_US_URL, "US API", "/");
    case "eu":
      return validateStudioUrl(process.env.EXPO_PUBLIC_FLIND_STUDIO_EU_URL, "EU API", "/");
  }
}

export function getFlindStudioOAuthClientId(region: "us" | "eu"): string {
  const id = region === "us"
    ? process.env.EXPO_PUBLIC_FLIND_STUDIO_OAUTH_US_CLIENT_ID
    : process.env.EXPO_PUBLIC_FLIND_STUDIO_OAUTH_EU_CLIENT_ID;
  if (!id || !/^[A-Za-z0-9_-]+$/.test(id)) {
    throw new Error("Flind Mobile Studio OAuth client for " + region + " is not configured");
  }
  return id;
}

export function getFlindStudioMcpUrl(region: StudioRegion): string {
  switch (region) {
    case "local":
      return validateStudioUrl(process.env.EXPO_PUBLIC_FLIND_STUDIO_MCP_LOCAL_URL ?? "http://localhost:8787/mcp", "local MCP", "/mcp");
    case "us":
      return validateStudioUrl(process.env.EXPO_PUBLIC_FLIND_STUDIO_MCP_US_URL, "US MCP", "/mcp");
    case "eu":
      return validateStudioUrl(process.env.EXPO_PUBLIC_FLIND_STUDIO_MCP_EU_URL, "EU MCP", "/mcp");
  }
}
