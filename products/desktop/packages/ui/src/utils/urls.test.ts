import { getBillingUrl, getPostHogUrl } from "@flind/ui/utils/urls";
import { afterEach, describe, expect, it, vi } from "vitest";

describe("getPostHogUrl", () => {
  it("returns null when no region is available and the input is a path", () => {
    expect(getPostHogUrl("/foo")).toBeNull();
  });

  it.each([
    ["us", "/foo", "https://us.posthog.com/foo"],
    ["us", "foo", "https://us.posthog.com/foo"],
    ["eu", "/foo", "https://eu.posthog.com/foo"],
  ] as const)(
    "joins base and path for %s region (path=%s)",
    (region, path, expected) => {
      expect(getPostHogUrl(path, region)).toBe(expected);
    },
  );

  it.each([
    "https://app.posthog.com/organization/billing",
    "http://localhost:8000/checkout",
    "HTTPS://us.posthog.com/foo",
  ])("passes absolute URLs through unchanged: %s", (url) => {
    expect(getPostHogUrl(url, "us")).toBe(url);
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
