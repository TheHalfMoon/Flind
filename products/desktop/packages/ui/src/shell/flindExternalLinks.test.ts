import { describe, expect, it } from "vitest";
import {
  verifyFlindExternalLink,
  verifyFlindCloudAppPath,
} from "./flindExternalLinks";

describe("Flind Desktop first-party public link boundary", () => {
  it("is closed until the first-party hostname and destination are configured", () => {
    expect(
      verifyFlindExternalLink("support", undefined, {
        support: "https://flind.example/support",
      }),
    ).toBeNull();
    expect(verifyFlindExternalLink("support", "flind.example", {})).toBeNull();
  });

  it("accepts exact owned HTTPS host and path", () => {
    expect(
      verifyFlindExternalLink("privacy", "flind.example", {
        privacy: "https://flind.example/privacy?version=1",
      }),
    ).toBe("https://flind.example/privacy?version=1");
    expect(
      verifyFlindExternalLink("docs", "FLIND.EXAMPLE", {
        docs: "https://flind.example/docs",
      }),
    ).toBe("https://flind.example/docs");
  });

  it.each([
    "https://posthog.com/privacy",
    "https://flind.example.evil.test/privacy",
    "http://flind.example/privacy",
    "https://flind.example:8443/privacy",
    "https://flind.example@evil.test/privacy",
    "https://user:password@flind.example/privacy",
    "javascript:alert(1)",
    "//flind.example/privacy",
    "https://flind.example/privacy#spoof",
    "not a url",
  ])("rejects unverified URL %s", (candidate) => {
    expect(
      verifyFlindExternalLink("privacy", "flind.example", {
        privacy: candidate,
      }),
    ).toBeNull();
  });

  it("does not allow an unowned community even when other Flind links are valid", () => {
    expect(
      verifyFlindExternalLink("community", "flind.example", {
        docs: "https://flind.example/docs",
        community: "https://discord.gg/legacy",
      }),
    ).toBeNull();
  });
});

describe("Flind independent cloud-app navigation", () => {
  it("fails closed without an explicitly configured hostname and base", () => {
    expect(
      verifyFlindCloudAppPath("/create-organization", undefined, undefined),
    ).toBeNull();
    expect(
      verifyFlindCloudAppPath(
        "/create-organization",
        "app.flind.example",
        undefined,
      ),
    ).toBeNull();
    expect(
      verifyFlindCloudAppPath(
        "/create-organization",
        undefined,
        "https://app.flind.example/",
      ),
    ).toBeNull();
  });

  it("constructs the expected first-party organization, project and image URLs", () => {
    const host = "app.flind.example";
    const base = "https://app.flind.example/";
    expect(verifyFlindCloudAppPath("/create-organization", host, base)).toBe(
      "https://app.flind.example/create-organization",
    );
    expect(
      verifyFlindCloudAppPath("/organization/create-project", host, base),
    ).toBe("https://app.flind.example/organization/create-project");
    expect(
      verifyFlindCloudAppPath("/uploaded_media/logo%2F1", host, base),
    ).toBe("https://app.flind.example/uploaded_media/logo%2F1");
  });

  it.each([
    ["https://posthog.com", "/create-organization"],
    ["https://app.flind.example.evil.test", "/create-organization"],
    ["http://app.flind.example", "/create-organization"],
    ["https://user@app.flind.example", "/create-organization"],
    ["https://app.flind.example:8443", "/create-organization"],
    ["https://app.flind.example/project/4", "/create-organization"],
    ["https://app.flind.example/?token=sensitive", "/create-organization"],
    ["https://app.flind.example/#frag", "/create-organization"],
    ["https://app.flind.example/", "//evil.test/"],
    ["https://app.flind.example/", "https://evil.test/"],
    ["https://app.flind.example/", "/\\evil.test"],
    ["https://app.flind.example/", "create-organization"],
  ])("rejects invalid base or path (%s, %s)", (base, path) => {
    expect(verifyFlindCloudAppPath(path, "app.flind.example", base)).toBeNull();
  });
});
