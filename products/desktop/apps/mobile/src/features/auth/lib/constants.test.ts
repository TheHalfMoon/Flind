import { afterEach, describe, expect, it, vi } from "vitest";
import { getCloudUrlFromRegion, getOauthClientIdFromRegion } from "./constants";

afterEach(() => vi.unstubAllEnvs());

describe("Flind mobile configured API origins", () => {
  it("fails closed for missing hosted regions and allows only local development by default", () => {
    vi.stubEnv("EXPO_PUBLIC_FLIND_API_US_URL", "");
    vi.stubEnv("EXPO_PUBLIC_FLIND_API_EU_URL", "");
    vi.stubEnv("EXPO_PUBLIC_FLIND_API_DEV_URL", "");
    expect(() => getCloudUrlFromRegion("us")).toThrow("not configured");
    expect(() => getCloudUrlFromRegion("eu")).toThrow("not configured");
    expect(() => getCloudUrlFromRegion("dev")).toThrow("not configured");
    vi.unstubAllEnvs();
    expect(getCloudUrlFromRegion("dev")).toBe("http://localhost:8010");
  });

  it("accepts configured HTTPS Flind instances and explicit loopback hosts", () => {
    vi.stubEnv("EXPO_PUBLIC_FLIND_API_US_URL", "https://flind.example:8443/");
    vi.stubEnv("EXPO_PUBLIC_FLIND_API_EU_URL", "https://eu.flind.example");
    vi.stubEnv("EXPO_PUBLIC_FLIND_API_DEV_URL", "http://127.0.0.1:8010");
    expect(getCloudUrlFromRegion("us")).toBe("https://flind.example:8443");
    expect(getCloudUrlFromRegion("eu")).toBe("https://eu.flind.example");
    expect(getCloudUrlFromRegion("dev")).toBe("http://127.0.0.1:8010");
  });

  it.each([
    "https://posthog.com",
    "https://us.posthog.com",
    "https://EU.POSTHOG.COM.",
    "http://public.example",
    "https://flind.example/path",
    "https://flind.example?token=secret",
    "https://flind.example#fragment",
    "https://user:secret@flind.example",
    "javascript:alert(1)",
    "https://flind.example ",
  ])("rejects inherited and unsafe API destinations: %s", (url) => {
    vi.stubEnv("EXPO_PUBLIC_FLIND_API_US_URL", url);
    expect(() => getCloudUrlFromRegion("us")).toThrow();
  });

  it("never guesses a hosted OAuth client registration", () => {
    vi.stubEnv("EXPO_PUBLIC_FLIND_OAUTH_US_CLIENT_ID", "");
    vi.stubEnv("EXPO_PUBLIC_FLIND_OAUTH_EU_CLIENT_ID", "");
    expect(() => getOauthClientIdFromRegion("us")).toThrow("not configured");
    expect(() => getOauthClientIdFromRegion("eu")).toThrow("not configured");
    vi.stubEnv("EXPO_PUBLIC_FLIND_OAUTH_US_CLIENT_ID", "flind-mobile-client_01");
    expect(getOauthClientIdFromRegion("us")).toBe("flind-mobile-client_01");
    vi.stubEnv("EXPO_PUBLIC_FLIND_OAUTH_US_CLIENT_ID", "invalid client id");
    expect(() => getOauthClientIdFromRegion("us")).toThrow();
  });
});
