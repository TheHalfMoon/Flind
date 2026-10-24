import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  externalUrlToAppPath,
  inboxReportShareUrl,
  slugifyTitle,
  universalUrl,
  getUniversalLinkOrigin,
} from "./deep-links";

describe("slugifyTitle", () => {
  it.each([
    ["null", null],
    ["undefined", undefined],
    ["empty string", ""],
    ["whitespace only", "   "],
    ["unsafe-only characters", ":::"],
  ])("returns an empty string when the title is %s", (_label, input) => {
    expect(slugifyTitle(input)).toBe("");
  });

  it("emits `--` for runs that mix a colon with other unsafe chars", () => {
    expect(slugifyTitle("fix(inbox): Add foo")).toBe("fix-inbox--Add-foo");
  });

  it("emits a single `-` for a colon-only run", () => {
    expect(slugifyTitle("feat:bar")).toBe("feat-bar");
  });

  it("preserves URL-unreserved punctuation (- _ . ~)", () => {
    expect(slugifyTitle("v1.2.3_final~ish")).toBe("v1.2.3_final~ish");
  });

  it("collapses runs of unsafe punctuation into a single hyphen", () => {
    expect(slugifyTitle("Cost $5, 50% off!")).toBe("Cost-5-50-off");
  });

  it("folds accented Latin letters to their ASCII base", () => {
    expect(slugifyTitle("café résumé naïve")).toBe("cafe-resume-naive");
  });

  it("hyphenizes non-Latin scripts that have no ASCII fold", () => {
    expect(slugifyTitle("Hello Привет world")).toBe("Hello-world");
  });

  it("preserves case", () => {
    expect(slugifyTitle("Hello World")).toBe("Hello-World");
  });
});

describe("inboxReportShareUrl", () => {
  it("returns just the UUID when no title argument is passed", () => {
    expect(inboxReportShareUrl("abc-123")).toBe("flind://inbox/abc-123");
  });

  it.each([
    ["null", null],
    ["undefined", undefined],
    ["empty string", ""],
  ])(
    "returns just the UUID when the title is %s",
    (_label, input: string | null | undefined) => {
      expect(inboxReportShareUrl("abc-123", input)).toBe(
        "flind://inbox/abc-123",
      );
    },
  );

  it("appends a slug derived from the title", () => {
    expect(inboxReportShareUrl("abc-123", "Hello World")).toBe(
      "flind://inbox/abc-123/Hello-World",
    );
  });

  it.each([
    ["unsafe-only characters", ":::"],
    ["whitespace only", "   "],
  ])("omits the slug when the title is %s", (_label, input) => {
    expect(inboxReportShareUrl("abc-123", input)).toBe(
      "flind://inbox/abc-123",
    );
  });

  it("preserves the desktop colon-run convention", () => {
    expect(inboxReportShareUrl("abc-123", "fix(inbox): Add foo")).toBe(
      "flind://inbox/abc-123/fix-inbox--Add-foo",
    );
  });
});

describe("universalUrl", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("does not invent a Flind universal link host", () => {
    vi.stubEnv("EXPO_PUBLIC_FLIND_UNIVERSAL_LINK_ORIGIN", "");
    expect(getUniversalLinkOrigin()).toBeNull();
    expect(() => universalUrl("/task/abc")).toThrow("not configured");
  });

  it("only creates HTTPS links for a configured Flind origin", () => {
    vi.stubEnv("EXPO_PUBLIC_FLIND_UNIVERSAL_LINK_ORIGIN", "https://links.flind.example");
    expect(universalUrl("/task/abc")).toBe("https://links.flind.example/task/abc");
  });

  it.each([
    "https://code.posthog.com",
    "https://code.posthog.com.",
    "http://links.flind.example",
    "https://user:secret@links.flind.example",
    "https://links.flind.example/extra",
    "https://links.flind.example?token=secret",
  ])("refuses an invalid universal link origin: %s", (host) => {
    vi.stubEnv("EXPO_PUBLIC_FLIND_UNIVERSAL_LINK_ORIGIN", host);
    expect(() => universalUrl("/task/abc")).toThrow();
  });
});

describe("externalUrlToAppPath", () => {
  beforeEach(() => {
    vi.stubEnv("EXPO_PUBLIC_FLIND_UNIVERSAL_LINK_ORIGIN", "https://links.flind.example");
  });
  afterEach(() => vi.unstubAllEnvs());


  it("returns the router path for a custom-scheme URL", () => {
    expect(externalUrlToAppPath("flind://task/task-123")).toBe(
      "/task/task-123",
    );
  });

  it("returns the router path for a universal-link URL", () => {
    expect(externalUrlToAppPath("https://links.flind.example/task/task-123")).toBe(
      "/task/task-123",
    );
  });

  it("preserves the query string", () => {
    expect(externalUrlToAppPath("flind://task/task-123?foo=bar")).toBe(
      "/task/task-123?foo=bar",
    );
  });

  it("strips a trailing slug segment from inbox custom-scheme URLs", () => {
    expect(
      externalUrlToAppPath("flind://inbox/report-abc/fix-inbox--Add-foo"),
    ).toBe("/inbox/report-abc");
  });

  it("strips a trailing slug segment from inbox universal links", () => {
    expect(
      externalUrlToAppPath(
        "https://links.flind.example/inbox/report-abc/Hello-World",
      ),
    ).toBe("/inbox/report-abc");
  });

  it("preserves the query string when stripping an inbox slug", () => {
    expect(
      externalUrlToAppPath("flind://inbox/report-abc/Hello-World?x=1"),
    ).toBe("/inbox/report-abc?x=1");
  });

  it("leaves a bare inbox URL untouched", () => {
    expect(externalUrlToAppPath("flind://inbox/report-abc")).toBe(
      "/inbox/report-abc",
    );
  });

  it.each([
    ["unrelated https host", "https://example.com/inbox/x"],
    ["unparseable string", "not a url"],
  ])("ignores URLs from %s", (_label, input) => {
    expect(externalUrlToAppPath(input)).toBe(null);
  });
});
