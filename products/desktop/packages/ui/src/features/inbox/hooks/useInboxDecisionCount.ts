import {
  buildPriorityFilterParam,
  buildSuggestedReviewerFilterParam,
} from "@flind/core/inbox/reportFiltering";
import {
  INBOX_SCOPE_FOR_YOU,
  parseTeammateInboxScope,
} from "@flind/core/inbox/reportMembership";
import { useOptionalAuthenticatedClient } from "@flind/ui/features/auth/authClient";
import { useCurrentUser } from "@flind/ui/features/auth/useCurrentUser";
import { useInboxReports } from "@flind/ui/features/inbox/hooks/useInboxReports";
import { useInboxReviewerScopeStore } from "@flind/ui/features/inbox/stores/inboxReviewerScopeStore";
import { useInboxSignalsFilterStore } from "@flind/ui/features/inbox/stores/inboxSignalsFilterStore";

const EMPTY_FILTER_ARRAY: never[] = [];

/**
 * The navigation badge needs only the ready-report count. Keeping it separate
 * from `useInboxSectionCounts` avoids polling the other two section counts on
 * every route.
 */
export function useInboxDecisionCount(options?: {
  enabled?: boolean;
  ignoreFilters?: boolean;
}): number {
  const enabled = options?.enabled ?? true;
  const ignoreFilters = options?.ignoreFilters ?? false;
  const scope = useInboxReviewerScopeStore((state) => state.scope);
  const sourceProductFilter = useInboxSignalsFilterStore((state) =>
    ignoreFilters ? EMPTY_FILTER_ARRAY : state.sourceProductFilter,
  );
  const priorityFilter = useInboxSignalsFilterStore((state) =>
    ignoreFilters ? EMPTY_FILTER_ARRAY : state.priorityFilter,
  );
  const isForYou = scope === INBOX_SCOPE_FOR_YOU;
  const teammateUuid = parseTeammateInboxScope(scope);
  const client = useOptionalAuthenticatedClient();
  const { data: currentUser } = useCurrentUser({
    client,
    enabled: enabled && isForYou && teammateUuid === null,
  });
  const reviewerUuid =
    teammateUuid ?? (isForYou ? (currentUser?.uuid ?? null) : null);
  const scopeReady = !isForYou || reviewerUuid !== null;
  const query = useInboxReports(
    {
      status: "ready",
      source_product:
        sourceProductFilter.length > 0
          ? sourceProductFilter.join(",")
          : undefined,
      priority: buildPriorityFilterParam(priorityFilter),
      suggested_reviewers: reviewerUuid
        ? buildSuggestedReviewerFilterParam([reviewerUuid])
        : undefined,
      count_only: true,
    },
    {
      enabled: enabled && scopeReady,
      refetchInterval: 60_000,
      refetchIntervalInBackground: false,
    },
  );

  return enabled ? (query.data?.count ?? 0) : 0;
}
