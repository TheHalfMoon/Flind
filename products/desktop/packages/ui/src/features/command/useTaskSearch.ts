import type { TaskSearchResult } from "@flind/shared/domain-types";
import { useAuthenticatedQuery } from "@flind/ui/hooks/useAuthenticatedQuery";

export function useTaskSearch(query: string, enabled: boolean) {
  return useAuthenticatedQuery<TaskSearchResult[]>(
    ["task-global-search", query],
    (client) => client.searchTasks(query),
    {
      enabled: enabled && query.length > 0,
      staleTime: 30_000,
      retry: false,
    },
  );
}
