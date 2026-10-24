import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { configureCustomCloud } from "./custom-cloud";
import { getOauthClientIdFromRegion, POSTHOG_DEV_CLIENT_ID } from "./oauth";
import {
  CLOUD_REGIONS,
  describeRegion,
  formatRegionBadge,
  REGION_LABELS,
} from "./regions";
import { getCloudUrlFromRegion } from "./urls";

beforeEach(() => {
  for (const key of [
    "FLIND_US_CLOUD_URL",
    "FLIND_US_OAUTH_CLIENT_ID",
    "FLIND_EU_CLOUD_URL",
    "FLIND_EU_OAUTH_CLIENT_ID",
    "FLIND_DEV_CLOUD_URL",
    "FLIND_DEV_CLOUD_OAUTH_CLIENT_ID",
    "POSTHOG_CUSTOM_CLOUD_URL",
    "POSTHOG_CUSTOM_CLOUD_OAUTH_CLIENT_ID",
  ]) {
    vi.stubEnv(key, "");
  }
});

afterEach(() => {
  configureCustomCloud(null);
  vi.unstubAllEnvs();
});

describe("hosted Flind cloud and OAuth identity", () => {
  it("refuses hosted regions when no independently owned cloud is configured", () => {
    for (const region of ["us", "eu", "dev-cloud"] as const) {
      expect(() => getCloudUrlFromRegion(region)).toThrow("not configured");
      expect(() => getOauthClientIdFromRegion(region)).toThrow(
        "not configured",
      );
    }
    expect(getCloudUrlFromRegion("dev")).toBe("http://localhost:8010");
    expect(getOauthClientIdFromRegion("dev")).toBe(POSTHOG_DEV_CLIENT_ID);
  });

  it("reads only valid independent endpoints and registered client IDs", () => {
    vi.stubEnv("FLIND_US_CLOUD_URL", "https://us.flind.example");
    vi.stubEnv("FLIND_US_OAUTH_CLIENT_ID", "us-flind-client-id");
    vi.stubEnv("FLIND_EU_CLOUD_URL", "https://eu.flind.example");
    vi.stubEnv("FLIND_EU_OAUTH_CLIENT_ID", "eu-flind-client-id");
    vi.stubEnv("FLIND_DEV_CLOUD_URL", "https://dev.flind.example");
    vi.stubEnv("FLIND_DEV_CLOUD_OAUTH_CLIENT_ID", "dev-flind-client-id");
    expect(getCloudUrlFromRegion("us")).toBe("https://us.flind.example");
    expect(getCloudUrlFromRegion("eu")).toBe("https://eu.flind.example");
    expect(getCloudUrlFromRegion("dev-cloud")).toBe(
      "https://dev.flind.example",
    );
    expect(getOauthClientIdFromRegion("us")).toBe("us-flind-client-id");
    expect(getOauthClientIdFromRegion("eu")).toBe("eu-flind-client-id");
    expect(getOauthClientIdFromRegion("dev-cloud")).toBe("dev-flind-client-id");
  });

  it("reads Vite-prefixed public Flind endpoints in browser builds", () => {
    vi.stubEnv("VITE_FLIND_US_CLOUD_URL", "https://web.flind.example");
    vi.stubEnv("VITE_FLIND_US_OAUTH_CLIENT_ID", "web-flind-client-id");
    expect(getCloudUrlFromRegion("us")).toBe("https://web.flind.example");
    expect(getOauthClientIdFromRegion("us")).toBe("web-flind-client-id");
  });

  it.each([
    ["https://us.posthog.com", "registered-client"],
    ["http://evil.example", "registered-client"],
    ["https://user@us.flind.example", "registered-client"],
    ["https://us.flind.example/project/1", "registered-client"],
    ["https://us.flind.example?token=secret", "registered-client"],
    ["https://us.flind.example", ""],
  ])("rejects unqualified US cloud pair %s", (url, oauthClientId) => {
    vi.stubEnv("FLIND_US_CLOUD_URL", url);
    vi.stubEnv("FLIND_US_OAUTH_CLIENT_ID", oauthClientId);
    expect(() => getCloudUrlFromRegion("us")).toThrow("not configured");
    expect(() => getOauthClientIdFromRegion("us")).toThrow("not configured");
  });
});

describe("custom Flind cloud", () => {
  it("is unavailable when no custom target is configured", () => {
    expect(() => getCloudUrlFromRegion("custom")).toThrow("not configured");
    expect(getOauthClientIdFromRegion("custom")).toBe("");
  });

  it("supports a separately configured custom target, not inherited hosted regions", () => {
    configureCustomCloud({
      url: "https://flind.private.example",
      oauthClientId: "custom-flind-client",
    });
    expect(getCloudUrlFromRegion("custom")).toBe(
      "https://flind.private.example",
    );
    expect(getOauthClientIdFromRegion("custom")).toBe("custom-flind-client");
    for (const region of ["us", "eu", "dev-cloud"] as const) {
      expect(() => getCloudUrlFromRegion(region)).toThrow("not configured");
    }
    expect(describeRegion("custom")).toMatchObject({
      label: "Custom",
      hint: "flind.private.example",
    });
  });
});

describe("Flind region labels", () => {
  it("uses clear first-party qualification hints, not donor hostnames", () => {
    expect(REGION_LABELS.us.hint).toBe("Configure Flind US Cloud");
    expect(REGION_LABELS.eu.hint).toBe("Configure Flind EU Cloud");
    expect(REGION_LABELS["dev-cloud"].hint).toBe("Configure Flind dev cloud");
    expect(REGION_LABELS.dev.hint).toBe("localhost:8010");
  });

  it("formats each known region consistently", () => {
    for (const region of CLOUD_REGIONS) {
      expect(formatRegionBadge(region)).toContain(REGION_LABELS[region].label);
    }
  });
});
