import type { ISetupStore } from "@flind/core/setup/identifiers";
import type { ActivityEntry } from "@flind/core/setup/setupState";
import type { DiscoveredTask } from "@flind/core/setup/types";
import {
  selectRepoDiscovery,
  selectRepoEnricher,
  useSetupStore,
} from "@flind/ui/features/setup/setupStore";

/**
 * Host delegate exposing the setup zustand store to the core `SetupRunService`.
 * Identical to the desktop adapter (apps/code renderer platform-adapters/setup):
 * the store is host-agnostic zustand, so web reuses it verbatim. Core writes UI
 * state through this narrow interface instead of importing `@flind/ui`.
 */
export const webSetupStore: ISetupStore = {
  getDiscoveryStatus: (repoPath) =>
    selectRepoDiscovery(useSetupStore.getState(), repoPath).status,
  getEnricherStatus: (repoPath) =>
    selectRepoEnricher(useSetupStore.getState(), repoPath).status,
  anyDiscoveryStarted: () =>
    Object.values(useSetupStore.getState().discoveryByRepo).some(
      (d) => d.status !== "idle",
    ),
  startDiscovery: (repoPath, taskId, taskRunId) =>
    useSetupStore.getState().startDiscovery(repoPath, taskId, taskRunId),
  completeDiscovery: (repoPath, tasks: DiscoveredTask[]) =>
    useSetupStore.getState().completeDiscovery(repoPath, tasks),
  failDiscovery: (repoPath, message) =>
    useSetupStore.getState().failDiscovery(repoPath, message),
  pushDiscoveryActivity: (repoPath, entry: ActivityEntry) =>
    useSetupStore.getState().pushDiscoveryActivity(repoPath, entry),
  startEnrichment: (repoPath) =>
    useSetupStore.getState().startEnrichment(repoPath),
  completeEnrichment: (repoPath) =>
    useSetupStore.getState().completeEnrichment(repoPath),
  failEnrichment: (repoPath) =>
    useSetupStore.getState().failEnrichment(repoPath),
  addEnricherSuggestionIfMissing: (task: DiscoveredTask) =>
    useSetupStore.getState().addEnricherSuggestionIfMissing(task),
};
