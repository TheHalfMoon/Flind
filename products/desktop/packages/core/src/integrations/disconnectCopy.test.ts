import { describe, expect, it } from "vitest";
import { buildGithubDisconnectDescription } from "./disconnectCopy";

describe("buildGithubDisconnectDescription", () => {
  it.each([
    [
      "project, last reference",
      false,
      "project" as const,
      "This uninstalls the Flind app from Flind on GitHub and disconnects it from every Flind project and personal account that uses it.",
    ],
    [
      "project, shared",
      true,
      "project" as const,
      "This project stops using GitHub. The Flind app stays installed on GitHub because other projects or accounts still use it.",
    ],
    [
      "account, shared",
      true,
      "account" as const,
      "Your account stops using GitHub. The Flind app stays installed on GitHub because other projects or accounts still use it.",
    ],
    [
      "account, last reference",
      false,
      "account" as const,
      "This uninstalls the Flind app from Flind on GitHub and disconnects it from every Flind project and personal account that uses it.",
    ],
  ])("%s", (_name, installationShared, scope, expected) => {
    expect(
      buildGithubDisconnectDescription("Flind", installationShared, scope),
    ).toBe(expected);
  });
});
