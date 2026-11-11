import type { UserCodexIntegration } from "@flind/api-client/posthog-client";
import {
  CODEX_CLOUD_ACCOUNT_SERVICE,
  type CodexCloudAccountService,
  type CodexCloudConnectResult,
} from "@flind/core/integrations/codexCloudAccountService";
import { useServiceOptional } from "@flind/di/react";
import { ANALYTICS_EVENTS } from "@flind/shared";
import { useOptionalAuthenticatedClient } from "@flind/ui/features/auth/authClient";
import { toast } from "@flind/ui/primitives/toast";
import { track } from "@flind/ui/shell/analytics";
import {
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

export const codexCloudAccountQueryKey = ["codex-cloud-account"] as const;

export function useCodexCloudAccount(): UseQueryResult<UserCodexIntegration> {
  const client = useOptionalAuthenticatedClient();
  return useQuery({
    queryKey: codexCloudAccountQueryKey,
    queryFn: () => {
      if (!client) throw new Error("Log in to Flind first.");
      return client.getCodexUserIntegration();
    },
    enabled: !!client,
    retry: false,
  });
}

export function useCodexCloudAccountService(): CodexCloudAccountService | null {
  return useServiceOptional<CodexCloudAccountService>(
    CODEX_CLOUD_ACCOUNT_SERVICE,
  );
}

export function useConnectCodexCloudAccount(): UseMutationResult<
  CodexCloudConnectResult,
  Error,
  string
> {
  const client = useOptionalAuthenticatedClient();
  const service = useCodexCloudAccountService();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (attemptId) => {
      if (!client) throw new Error("Log in to Flind first.");
      if (!service)
        throw new Error("ChatGPT login is unavailable on this device.");
      return service.connect(attemptId, client);
    },
    onSuccess: ({ integration, staleFileError }) => {
      queryClient.setQueryData(codexCloudAccountQueryKey, integration);
      track(ANALYTICS_EVENTS.CODEX_CLOUD_ACCOUNT_CONNECTED);
      if (staleFileError) {
        toast.warning("ChatGPT account connected", {
          description: `Desktop could not delete the old login file. Remove ~/.codex-posthog/auth.json by hand. ${staleFileError.message}`,
        });
      } else {
        toast.success("ChatGPT account connected");
      }
    },
  });
}

export function useDisconnectCodexCloudAccount(): UseMutationResult<
  void,
  Error,
  void
> {
  const client = useOptionalAuthenticatedClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => {
      if (!client) throw new Error("Log in to Flind first.");
      return client.disconnectCodexUserIntegration();
    },
    onSuccess: () => {
      queryClient.setQueryData<UserCodexIntegration>(
        codexCloudAccountQueryKey,
        {
          status: "not_connected",
          plan_type: null,
          email: null,
          connected_at: null,
        },
      );
    },
  });
}
