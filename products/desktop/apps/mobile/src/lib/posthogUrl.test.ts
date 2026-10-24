import { describe, expect, it } from "vitest";
import { parsePostHogUrl } from "./posthogUrl";

const hosts = {
  appBaseUrl: "https://us.flind.example",
  codeBaseUrl: "https://code.flind.example",
};

describe("Flind mobile first-party Markdown reference links", () => {
  it("does not implicitly trust inherited vendor URLs", () => {
    for (const url of [
      "https://posthog.com/docs/session-replay",
      "https://posthog.com/pricing",
      "https://us.posthog.com/project/1/dashboard/42",
      "https://code.posthog.com/task/task-123",
    ]) {
      expect(parsePostHogUrl(url, hosts)).toBeNull();
    }
  });

  it("does not treat any URL as first-party without explicit Flind hosts", () => {
    expect(parsePostHogUrl("https://us.flind.example/insights/42")).toBeNull();
    expect(parsePostHogUrl("https://code.flind.example/task/abc")).toBeNull();
  });

  it("labels task and run references on an approved Flind code host", () => {
    expect(
      parsePostHogUrl("https://code.flind.example/task/task-123/run/run-456", hosts),
    ).toEqual({
      kind: "code",
      defaultLabel: "Code / Task run (run-456)",
      normalizedUrl: "https://code.flind.example/task/task-123/run/run-456",
      refId: "run-456",
    });
  });

  it.each([
    "project/7/feature_flags",
    "project/7/feature-flags",
    "feature_flags",
    "feature-flags",
  ])("labels the %s Flind feature flag reference", (section) => {
    expect(
      parsePostHogUrl("https://us.flind.example/" + section + "/42", hosts)?.defaultLabel,
    ).toBe("Feature flag (42)");
  });

  it("labels SQL queries and feature flag filters on a configured app host", () => {
    expect(
      parsePostHogUrl(
        "https://us.flind.example/project/7/sql?open_query=SELECT%201",
        hosts,
      )?.defaultLabel,
    ).toBe("SQL query");
    expect(
      parsePostHogUrl(
        "https://us.flind.example/project/1/feature-flags?search=checkout",
        hosts,
      )?.defaultLabel,
    ).toBe("Feature flags / checkout");
  });

  it("recognizes relative task or app paths using their approved destinations", () => {
    expect(parsePostHogUrl("/task/abc", hosts)?.kind).toBe("code");
    expect(parsePostHogUrl("/insights/abc", hosts)?.kind).toBe("app");
  });

  it("supports one self-hosted Flind origin for code and app without mislabeling", () => {
    const shared = {
      appBaseUrl: "https://selfhost.flind.example",
      codeBaseUrl: "https://selfhost.flind.example",
    };
    expect(parsePostHogUrl("/task/abc", shared)?.kind).toBe("code");
    expect(parsePostHogUrl("/insights/abc", shared)?.kind).toBe("app");
  });

  it("accepts loopback only for explicit local HTTP development", () => {
    expect(
      parsePostHogUrl("/insights/1", {
        appBaseUrl: "http://localhost:8010",
      })?.kind,
    ).toBe("app");
    expect(
      parsePostHogUrl("/insights/1", {
        appBaseUrl: "http://public.flind.example",
      }),
    ).toBeNull();
  });

  it("rejects unsafe, inherited or spoofed configuration", () => {
    for (const appBaseUrl of [
      "https://us.posthog.com",
      "https://eu.posthog.com.",
      "http://external.example",
      "https://user:secret@us.flind.example",
      "https://us.flind.example/extra",
      "https://us.flind.example?x=secret",
    ]) {
      expect(
        parsePostHogUrl("https://us.flind.example/insights/1", { appBaseUrl }),
      ).toBeNull();
    }
    expect(
      parsePostHogUrl("https://us.flind.example.attacker.test/insights/1", hosts),
    ).toBeNull();
  });

  it("does not upgrade web/marketing links to first-party chips", () => {
    expect(parsePostHogUrl("https://flind.example/pricing", hosts)).toBeNull();
    expect(parsePostHogUrl("https://example.com/docs/session-replay", hosts)).toBeNull();
  });
});
