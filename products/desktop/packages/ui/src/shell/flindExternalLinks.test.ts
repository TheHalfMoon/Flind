import { describe, expect, it } from "vitest";
import { verifyFlindExternalLink } from "./flindExternalLinks";

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
