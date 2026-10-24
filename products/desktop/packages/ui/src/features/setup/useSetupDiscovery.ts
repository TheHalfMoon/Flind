import { SetupRunService } from "@flind/core/setup/setupRunService";
import { useService } from "@flind/di/react";
import { DISCOVERY_RUN_FLAG } from "@flind/shared";
import { useFeatureFlag } from "@flind/ui/features/feature-flags/useFeatureFlag";
import { useEffect } from "react";
import { useActiveRepoStore } from "../../shell/activeRepoStore";

export function useSetupDiscovery() {
  const selectedDirectory = useActiveRepoStore((s) => s.path);
  const service = useService(SetupRunService);
  const discoveryEnabled = useFeatureFlag(DISCOVERY_RUN_FLAG);

  useEffect(() => {
    if (!selectedDirectory) return;
    service.maybeStart(selectedDirectory, discoveryEnabled);
  }, [selectedDirectory, service, discoveryEnabled]);
}
