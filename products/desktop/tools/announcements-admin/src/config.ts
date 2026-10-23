// Configure these values for a Flind-owned deployment before using this admin tool.
export const FLIND_HOST = import.meta.env.VITE_FLIND_HOST || "http://localhost:8010";
export const PROJECT_ID = Number(import.meta.env.VITE_FLIND_PROJECT_ID || "0");
export const CLIENT_ID = import.meta.env.VITE_FLIND_OAUTH_CLIENT_ID || "";
export const REDIRECT_URI = `${window.location.origin}/oauth/callback`;
export const OAUTH_SCOPES = "feature_flag:read feature_flag:write user:read";
