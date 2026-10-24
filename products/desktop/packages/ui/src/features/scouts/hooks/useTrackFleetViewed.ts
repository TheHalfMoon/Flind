import type { ScoutConfig } from "@flind/api-client/posthog-client";
import { getScoutOrigin } from "@flind/core/scouts/scoutPresentation";
import type { ScoutFleetSyncOutcome } from "@flind/shared";
import { ANALYTICS_EVENTS } from "@flind/shared";
import { track } from "@flind/ui/shell/analytics";
import { useEffect, useRef } from "react";
import { useAuthStateValue } from "../../auth/store";

export function useTrackFleetViewed(
  configs: ScoutConfig[] | undefined,
  syncOutcome: ScoutFleetSyncOutcome | null,
  ready = true,
) {
  const projectId = useAuthStateValue((state) => state.currentProjectId);
  const tracked = useRef<number | null>(null);
  useEffect(() => {
    // Wait for the sync to settle, so a fleet the sync is about to change is
    // never reported against an outcome the request has not reached yet.
    if (
      !projectId ||
      tracked.current === projectId ||
      syncOutcome === null ||
      !ready ||
      !configs
    )
      return;
    tracked.current = projectId;
    track(ANALYTICS_EVENTS.SCOUT_FLEET_VIEWED, {
      scout_count: configs.length,
      enabled_count: configs.filter((config) => config.enabled).length,
      dry_run_count: configs.filter((config) => !config.emit).length,
      custom_count: configs.filter(
        (config) => getScoutOrigin(config) === "custom",
      ).length,
      is_empty: configs.length === 0,
      sync_outcome: syncOutcome,
    });
  }, [configs, syncOutcome, ready, projectId]);
}
