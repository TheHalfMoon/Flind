import type {
  Integration,
  RepositoryOption,
  RepositorySelection,
  UserGithubIntegration,
} from "../types";

/** Normalize legacy environment-scoped integration IDs for the numeric
 * repository-picker contract. User-scoped UUID integrations have their own
 * path (buildUserRepositoryOptions) and must not be coerced to NaN. */
export function normalizeLegacyGithubIntegrations(
  items: readonly {
    kind: string;
    id: number | string;
    [key: string]: unknown;
  }[],
): Integration[] {
  return items.flatMap((item) => {
    if (item.kind !== "github") return [];
    const id =
      typeof item.id === "number"
        ? item.id
        : /^[1-9][0-9]*$/.test(item.id)
          ? Number(item.id)
          : Number.NaN;
    if (!Number.isSafeInteger(id) || id <= 0) return [];
    const display_name =
      typeof item.display_name === "string" ? item.display_name : undefined;
    const rawConfig = item.config;
    const account =
      typeof rawConfig === "object" &&
      rawConfig !== null &&
      "account" in rawConfig
        ? rawConfig.account
        : undefined;
    const login =
      typeof account === "object" && account !== null && "login" in account
        ? account.login
        : undefined;
    return [
      {
        id,
        kind: "github",
        display_name,
        ...(typeof login === "string"
          ? { config: { account: { login } } }
          : {}),
      },
    ];
  });
}

function getIntegrationLabel(integration: Integration): string {
  return (
    integration.display_name ??
    integration.config?.account?.login ??
    `GitHub ${integration.id}`
  );
}

export function buildRepositoryOptions(
  integrations: Integration[],
  repositoriesByIntegration: Record<number, string[]>,
): RepositoryOption[] {
  return integrations
    .flatMap((integration) =>
      (repositoriesByIntegration[integration.id] ?? []).map((repository) => ({
        integrationId: integration.id,
        integrationLabel: getIntegrationLabel(integration),
        repository,
      })),
    )
    .sort((left, right) => left.repository.localeCompare(right.repository));
}

export function buildUserRepositoryOptions(
  integrations: UserGithubIntegration[],
  repositoriesByInstallation: Record<string, string[]>,
): RepositoryOption[] {
  return integrations
    .flatMap((integration) =>
      (repositoriesByInstallation[integration.installation_id] ?? []).map(
        (repository) => ({
          integrationId: Number(integration.installation_id),
          integrationLabel:
            integration.account?.name ??
            `GitHub ${integration.installation_id}`,
          repository,
        }),
      ),
    )
    .sort((left, right) => left.repository.localeCompare(right.repository));
}

export function repositoryOptionsEqual(
  left: RepositoryOption[],
  right: RepositoryOption[],
): boolean {
  return (
    left.length === right.length &&
    left.every((option, index) => {
      const other = right[index];
      return (
        other?.integrationId === option.integrationId &&
        other.integrationLabel === option.integrationLabel &&
        other.repository === option.repository
      );
    })
  );
}

export function repositoryLoadWarning(
  failedCount: number,
  totalCount: number,
): string | null {
  if (failedCount === 0) return null;
  return failedCount === totalCount
    ? "Could not load GitHub repositories. Pull to retry."
    : "Some GitHub repositories could not be loaded. Pull to retry.";
}

export function findRepositoryOption(
  options: RepositoryOption[],
  selection: RepositorySelection,
): RepositoryOption | null {
  if (!selection.integrationId || !selection.repository) return null;
  return (
    options.find(
      (option) =>
        option.integrationId === selection.integrationId &&
        option.repository === selection.repository,
    ) ?? null
  );
}

export function toRepositorySelection(
  option: RepositoryOption | null,
): RepositorySelection {
  return {
    integrationId: option?.integrationId ?? null,
    repository: option?.repository ?? null,
  };
}

export function isRepositorySelectionComplete(
  selection: RepositorySelection,
): boolean {
  return !!selection.integrationId && !!selection.repository;
}
