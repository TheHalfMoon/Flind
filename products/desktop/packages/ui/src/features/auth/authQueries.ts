import type { AuthState } from "@flind/core/auth/schemas";
import { resolveService } from "@flind/di/container";
import {
  HOST_TRPC_CLIENT,
  type HostTrpcClient,
} from "@flind/host-router/client";
import { useIntegrationStore } from "@flind/ui/features/integrations/store";
import { clearQuerySnapshots } from "@flind/ui/hooks/useQuerySnapshot";
import {
  IMPERATIVE_QUERY_CLIENT,
  type ImperativeQueryClient,
} from "@flind/ui/shell/queryClient";
import { getAuthIdentity, useAuthStore } from "./store";

export type { AuthState };
export { getAuthIdentity };

export { useAuthStateValue } from "./store";
export { useCurrentUser } from "./useCurrentUser";

function hostClient(): HostTrpcClient {
  return resolveService<HostTrpcClient>(HOST_TRPC_CLIENT);
}

function queryClient(): ImperativeQueryClient {
  return resolveService<ImperativeQueryClient>(IMPERATIVE_QUERY_CLIENT);
}

export async function fetchAuthState(): Promise<AuthState> {
  return await hostClient().auth.getState.query();
}

export async function refreshAuthStateQuery(): Promise<void> {
  const state = await fetchAuthState();
  useAuthStore.getState().setAuthState(state);
}

export function clearAuthScopedQueries(): void {
  useIntegrationStore.getState().setIntegrations([], null);
  queryClient().removeQueries({
    predicate: (query) => query.meta?.authScoped === true,
  });
  clearQuerySnapshots();
}
