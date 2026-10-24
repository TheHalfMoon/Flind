import { afterEach, describe, expect, it, vi } from "vitest";
import {
  getFlindStudioApiHost,
  getFlindStudioMcpUrl,
  getFlindStudioOAuthClientId,
} from "./config";

afterEach(() => vi.unstubAllEnvs());

describe("Flind Mobile Studio egress configuration", () => {
  it("does not assume inherited cloud or OAuth providers exist", () => {
    vi.stubEnv("EXPO_PUBLIC_FLIND_STUDIO_US_URL", "");
    vi.stubEnv("EXPO_PUBLIC_FLIND_STUDIO_MCP_US_URL", "");
    vi.stubEnv("EXPO_PUBLIC_FLIND_STUDIO_OAUTH_US_CLIENT_ID", "");
    expect(() => getFlindStudioApiHost("us")).toThrow("not configured");
    expect(() => getFlindStudioMcpUrl("us")).toThrow("not configured");
    expect(() => getFlindStudioOAuthClientId("us")).toThrow("not configured");
    expect(getFlindStudioMcpUrl("local")).toBe("http://localhost:8787/mcp");
  });

  it("supports explicit HTTPS origins and locally configured MCP endpoints", () => {
    vi.stubEnv("EXPO_PUBLIC_FLIND_STUDIO_EU_URL", "https://eu.flind.example/");
    vi.stubEnv("EXPO_PUBLIC_FLIND_STUDIO_MCP_EU_URL", "https://mcp.flind.example/mcp");
    vi.stubEnv("EXPO_PUBLIC_FLIND_STUDIO_OAUTH_EU_CLIENT_ID", "flind-studio-client_1");
    expect(getFlindStudioApiHost("eu")).toBe("https://eu.flind.example");
    expect(getFlindStudioMcpUrl("eu")).toBe("https://mcp.flind.example/mcp");
    expect(getFlindStudioOAuthClientId("eu")).toBe("flind-studio-client_1");
  });

  it.each([
    "https://posthog.com",
    "https://mcp.posthog.com",
    "https://mcp-eu.posthog.com.",
    "http://external.example",
    "https://mcp.flind.example/path",
    "https://user:pass@mcp.flind.example",
    "https://mcp.flind.example?token=secret",
  ])("rejects unsafe configured MCP destinations: %s", (url) => {
    vi.stubEnv("EXPO_PUBLIC_FLIND_STUDIO_MCP_US_URL", url);
    expect(() => getFlindStudioMcpUrl("us")).toThrow();
  });
});
