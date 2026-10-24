import { useHostTRPC } from "@flind/host-router/react";
import { getCloudUrlFromRegion } from "@flind/shared";
import { useAuthStateValue } from "@flind/ui/features/auth/store";
import { stripDisabledModels } from "@flind/ui/features/sessions/modelOptionFilters";
import { useModelRolloutFlags } from "@flind/ui/features/sessions/useModelRolloutFlags";
import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";

export function usePiModelCatalog(enabled: boolean) {
  const trpc = useHostTRPC();
  const cloudRegion = useAuthStateValue((state) => state.cloudRegion);
  const modelFlags = useModelRolloutFlags();
  const apiHost = useMemo(
    () => (cloudRegion ? getCloudUrlFromRegion(cloudRegion) : null),
    [cloudRegion],
  );

  return useQuery({
    ...trpc.agent.getPiModelCatalog.queryOptions({
      apiHost: apiHost ?? "",
      region: cloudRegion ?? "us",
    }),
    enabled: enabled && apiHost !== null,
    select: (models) => stripDisabledModels(models, modelFlags),
  });
}
