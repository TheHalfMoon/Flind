import { describe, expect, it } from "vitest";
import {
  buildRepositoryOptions,
  buildUserRepositoryOptions,
  normalizeLegacyGithubIntegrations,
  findRepositoryOption,
  isRepositorySelectionComplete,
  repositoryLoadWarning,
  repositoryOptionsEqual,
  toRepositorySelection,
} from "./repositorySelection";

describe("repositorySelection", () => {
  it("normalizes numeric legacy GitHub IDs without accepting UUIDs or malformed IDs", () => {
    expect(
      normalizeLegacyGithubIntegrations([
        { id: "42", kind: "github", display_name: "Flind" },
        { id: 7, kind: "github", config: { account: { login: "operator" } } },
        { id: "uuid-1", kind: "github", display_name: "Unknown" },
        { id: "0042", kind: "github" },
        { id: "3.5", kind: "github" },
        { id: 0, kind: "github" },
        { id: Number.MAX_SAFE_INTEGER + 1, kind: "github" },
        { id: 4, kind: "google" },
      ]),
    ).toEqual([
      { id: 42, kind: "github", display_name: "Flind" },
      {
        id: 7,
        kind: "github",
        display_name: undefined,
        config: { account: { login: "operator" } },
      },
    ]);
  });

  const integrations = [
    { id: 7, kind: "github", display_name: "Personal GitHub" },
    {
      id: 11,
      kind: "github",
      config: { account: { login: "posthog" } },
    },
  ];

  it("preserves integration identity for each repository option", () => {
    expect(
      buildRepositoryOptions(integrations, {
        7: ["annika/mobile-app"],
        11: ["posthog/posthog", "posthog/code"],
      }),
    ).toEqual([
      {
        integrationId: 7,
        integrationLabel: "Personal GitHub",
        repository: "annika/mobile-app",
      },
      {
        integrationId: 11,
        integrationLabel: "posthog",
        repository: "posthog/code",
      },
      {
        integrationId: 11,
        integrationLabel: "posthog",
        repository: "posthog/posthog",
      },
    ]);
  });

  it("finds an exact repository option", () => {
    const options = buildRepositoryOptions(integrations, {
      7: ["posthog/posthog"],
      11: ["posthog/posthog"],
    });

    expect(
      findRepositoryOption(options, {
        integrationId: 11,
        repository: "posthog/posthog",
      }),
    ).toEqual({
      integrationId: 11,
      integrationLabel: "posthog",
      repository: "posthog/posthog",
    });
  });

  it.each([
    [
      {
        id: "user-42",
        kind: "github",
        installation_id: "42",
        account: { name: "PostHog" },
      },
      "PostHog",
    ],
    [{ id: "user-43", kind: "github", installation_id: "43" }, "GitHub 43"],
  ])(
    "builds user integration options with the expected label",
    (integration, integrationLabel) => {
      expect(
        buildUserRepositoryOptions([integration], {
          [integration.installation_id]: ["posthog/code"],
        }),
      ).toEqual([
        {
          integrationId: Number(integration.installation_id),
          integrationLabel,
          repository: "posthog/code",
        },
      ]);
    },
  );

  it("treats a changed label as a different repository option", () => {
    const option = {
      integrationId: 11,
      integrationLabel: "posthog",
      repository: "posthog/code",
    };

    expect(
      repositoryOptionsEqual(
        [option],
        [{ ...option, integrationLabel: "PostHog GitHub" }],
      ),
    ).toBe(false);
  });

  it.each([
    [0, 2, null],
    [1, 2, "Some GitHub repositories could not be loaded. Pull to retry."],
    [2, 2, "Could not load GitHub repositories. Pull to retry."],
  ])(
    "maps repository failures to the expected warning",
    (failedCount, totalCount, expected) => {
      expect(repositoryLoadWarning(failedCount, totalCount)).toBe(expected);
    },
  );

  it("converts an option into a repository selection", () => {
    const selection = toRepositorySelection({
      integrationId: 11,
      integrationLabel: "posthog",
      repository: "posthog/code",
    });

    expect(selection).toEqual({
      integrationId: 11,
      repository: "posthog/code",
    });
    expect(isRepositorySelectionComplete(selection)).toBe(true);
  });
});
