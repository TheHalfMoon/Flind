import type { SessionConfigOption } from "@agentclientprotocol/sdk";
import { useHostTRPCClient } from "@flind/host-router/react";
import { getCloudUrlFromRegion } from "@flind/shared";
import { useAuthStateValue } from "@flind/ui/features/auth/store";
import type { LoopSchemas } from "@flind/ui/features/loops/loopSchemas";
import { useQuery } from "@tanstack/react-query";

/**
 * The per-adapter session config options (models, efforts) the main
 * create-task picker is built from, for reuse by the loop form's static
 * pickers. No agent session is created.
 */
export function useLoopModelConfigOptions(
  adapter: LoopSchemas.LoopRuntimeAdapterEnum,
): SessionConfigOption[] {
  const hostClient = useHostTRPCClient();
  const cloudRegion = useAuthStateValue((state) => state.cloudRegion);
  const { data } = useQuery({
    queryKey: ["loops", "model-config-options", cloudRegion, adapter],
    queryFn: ({ signal }) => {
      if (!cloudRegion) return [];
      return hostClient.agent.getPreviewConfigOptions.query(
        { apiHost: getCloudUrlFromRegion(cloudRegion), adapter },
        { signal },
      );
    },
    enabled: !!cloudRegion,
    staleTime: 5 * 60_000,
  });
  return data ?? [];
}
