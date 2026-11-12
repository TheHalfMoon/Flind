import type { RootLogger } from "@flind/di/logger";
import { afterEach, describe, expect, it, vi } from "vitest";
import { WebOAuthFlowService } from "./web-oauth-flow";

const log = {
  info: vi.fn(),
  warn: vi.fn(),
} as unknown as RootLogger;

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("Flind Web OAuth fail-closed Cloud identity", () => {
  it("does not contact an inherited hosted region without an independent endpoint and OAuth ID", async () => {
    vi.stubEnv("FLIND_US_CLOUD_URL", "");
    vi.stubEnv("FLIND_US_OAUTH_CLIENT_ID", "");
    const fetcher = vi.fn();
    vi.stubGlobal("fetch", fetcher);
    const flow = new WebOAuthFlowService(log);
    const result = await flow.refreshToken("not-a-real-token", "us");
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error).toContain("Flind us Cloud is not configured");
    }
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("uses only a Flind-registered OAuth ID and verified Flind host when configured", async () => {
    vi.stubEnv("FLIND_US_CLOUD_URL", "https://us.flind.example");
    vi.stubEnv("FLIND_US_OAUTH_CLIENT_ID", "flind-published-client-id");
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ error: "authorization_pending" }), {
        status: 401,
        statusText: "Unauthorized",
      }),
    );
    vi.stubGlobal("fetch", fetcher);
    const flow = new WebOAuthFlowService(log);
    const result = await flow.refreshToken("test-placeholder", "us");
    expect(result.success).toBe(false);
    expect(fetcher).toHaveBeenCalledOnce();
    const [endpoint, init] = fetcher.mock.calls[0];
    expect(endpoint).toBe("https://us.flind.example/oauth/token");
    const request = JSON.parse(init.body as string);
    expect(request.client_id).toBe("flind-published-client-id");
    expect(request.refresh_token).toBe("test-placeholder");
  });

  it.each([301, 302, 303, 307, 308])(
    "rejects HTTP %s before an OAuth refresh token can leave the selected Flind host",
    async (status) => {
      vi.stubEnv("FLIND_US_CLOUD_URL", "https://us.flind.example");
      vi.stubEnv("FLIND_US_OAUTH_CLIENT_ID", "flind-owned-client");
      const fetcher = vi.fn().mockResolvedValue(
        new Response(null, {
          status,
          headers: { Location: "https://attacker.invalid/collect" },
        }),
      );
      vi.stubGlobal("fetch", fetcher);

      const result = await new WebOAuthFlowService(log).refreshToken(
        "synthetic-refresh-secret",
        "us",
      );

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error).toContain("prohibited redirect");
      }
      expect(fetcher).toHaveBeenCalledOnce();
      const [url, init] = fetcher.mock.calls[0];
      expect(url).toBe("https://us.flind.example/oauth/token");
      expect(init).toEqual(
        expect.objectContaining({ method: "POST", redirect: "error" }),
      );
      expect(JSON.parse(init.body)).toEqual(
        expect.objectContaining({
          grant_type: "refresh_token",
          refresh_token: "synthetic-refresh-secret",
          client_id: "flind-owned-client",
        }),
      );
    },
  );

  it("rejects a browser redirect error without retrying the OAuth token body", async () => {
    vi.stubEnv("FLIND_US_CLOUD_URL", "https://us.flind.example");
    vi.stubEnv("FLIND_US_OAUTH_CLIENT_ID", "flind-owned-client");
    const fetcher = vi
      .fn()
      .mockRejectedValue(
        new TypeError("Fetch blocked redirect by request policy"),
      );
    vi.stubGlobal("fetch", fetcher);
    const result = await new WebOAuthFlowService(log).refreshToken(
      "synthetic-refresh-secret",
      "us",
    );
    expect(result.success).toBe(false);
    expect(fetcher).toHaveBeenCalledOnce();
    expect(fetcher.mock.calls[0][1].redirect).toBe("error");
  });

  it("rejects configured vendor domain even when an OAuth ID is supplied", async () => {
    vi.stubEnv("FLIND_EU_CLOUD_URL", "https://eu.posthog.com");
    vi.stubEnv("FLIND_EU_OAUTH_CLIENT_ID", "seemingly-valid-client-id");
    const fetcher = vi.fn();
    vi.stubGlobal("fetch", fetcher);
    const result = await new WebOAuthFlowService(log).refreshToken(
      "test-placeholder",
      "eu",
    );
    expect(result.success).toBe(false);
    expect(fetcher).not.toHaveBeenCalled();
  });
});
