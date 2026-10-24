import { getBillingUrl, getPostHogUrl } from "@flind/ui/utils/urls";
import { afterEach, describe, expect, it, vi } from "vitest";

describe("getPostHogUrl first-party-only project navigation", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("refuses region-derived inherited hosts without an independent Flind app", () => {
    vi.stubEnv("VITE_FLIND_CLOUD_APP_HOST", "");
    vi.stubEnv("VITE_FLIND_CLOUD_APP_URL", "");
    expect(getPostHogUrl("/foo")).toBeNull();
    expect(getPostHogUrl("/foo", "us")).toBeNull();
    expect(getPostHogUrl("/foo", "eu")).toBeNull();
    expect(getPostHogUrl("https://us.posthog.com/project/1", "us")).toBeNull();
  });

  it.each([
    [
      "us",
      "/project/42/insights",
      "https://app.flind.example/project/42/insights",
    ],
    ["eu", "project/42/replay", "https://app.flind.example/project/42/replay"],
    [
      "us",
      "/uploaded_media/icon%2F1",
      "https://app.flind.example/uploaded_media/icon%2F1",
    ],
  ] as const)(
    "uses the first-party host regardless of legacy region %s",
    (region, path, expected) => {
      vi.stubEnv("VITE_FLIND_CLOUD_APP_HOST", "app.flind.example");
      vi.stubEnv("VITE_FLIND_CLOUD_APP_URL", "https://app.flind.example/");
      expect(getPostHogUrl(path, region)).toBe(expected);
    },
  );

  it("allows verified absolute Flind app URLs from server payloads", () => {
    vi.stubEnv("VITE_FLIND_CLOUD_APP_HOST", "app.flind.example");
    vi.stubEnv("VITE_FLIND_CLOUD_APP_URL", "https://app.flind.example/");
    expect(getPostHogUrl("https://app.flind.example/project/1", "us")).toBe(
      "https://app.flind.example/project/1",
    );
  });

  it.each([
    "https://app.posthog.com/organization/billing",
    "http://localhost:8000/checkout",
    "HTTPS://us.posthog.com/foo",
    "https://app.flind.example.evil.test/foo",
    "http://app.flind.example/foo",
    "https://user@app.flind.example/foo",
    "https://app.flind.example:8443/foo",
    "https://app.flind.example/foo#spoof",
    "//evil.test/other",
    "/\\evil.test",
    "javascript:alert(1)",
  ])("refuses unverified absolute or confusing URL %s", (url) => {
    vi.stubEnv("VITE_FLIND_CLOUD_APP_HOST", "app.flind.example");
    vi.stubEnv("VITE_FLIND_CLOUD_APP_URL", "https://app.flind.example/");
    expect(getPostHogUrl(url, "us")).toBeNull();
  });
});

describe("getBillingUrl first-party billing boundary", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("returns null when billing is not explicitly configured in any region", () => {
    vi.stubEnv("VITE_FLIND_CLOUD_APP_HOST", "");
    vi.stubEnv("VITE_FLIND_BILLING_URL", "");
    expect(getBillingUrl()).toBeNull();
    expect(getBillingUrl("us")).toBeNull();
    expect(getBillingUrl("eu")).toBeNull();
  });

  it("uses only the explicitly configured first-party Flind billing URL", () => {
    vi.stubEnv("VITE_FLIND_CLOUD_APP_HOST", "app.flind.example");
    vi.stubEnv("VITE_FLIND_BILLING_URL", "https://app.flind.example/billing");
    expect(getBillingUrl("us")).toBe("https://app.flind.example/billing");
    expect(getBillingUrl("eu")).toBe("https://app.flind.example/billing");
  });

  it.each([
    "https://us.posthog.com/organization/billing/overview",
    "https://app.flind.example.evil.test/billing",
    "http://app.flind.example/billing",
    "https://user@app.flind.example/billing",
    "https://app.flind.example:4443/billing",
    "https://app.flind.example/billing#secret",
  ])("rejects unsafe or inherited billing destination %s", (url) => {
    vi.stubEnv("VITE_FLIND_CLOUD_APP_HOST", "app.flind.example");
    vi.stubEnv("VITE_FLIND_BILLING_URL", url);
    expect(getBillingUrl("us")).toBeNull();
  });
});
