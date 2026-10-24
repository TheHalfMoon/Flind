import { buildInboxViewedProperties } from "@flind/core/inbox/engagement";
import type { InboxReviewerScope } from "@flind/shared/analytics-events";
import { ANALYTICS_EVENTS } from "@flind/shared/analytics-events";
import type { SignalReport } from "@flind/shared/types";
import { track } from "@flind/ui/shell/analytics";
import { useEffect, useRef } from "react";

export function useTrackReportsInboxViewed({
  reports,
  totalCount,
  isReady,
  sourceProductFilter,
  priorityFilter,
  searchQuery,
  scope,
  reportStateFilter,
  defaultReportStateFilter,
}: {
  reports: SignalReport[];
  totalCount: number;
  isReady: boolean;
  sourceProductFilter: string[];
  priorityFilter: string[];
  searchQuery: string;
  scope: InboxReviewerScope;
  reportStateFilter: readonly string[];
  defaultReportStateFilter: readonly string[];
}): void {
  const firedRef = useRef(false);

  useEffect(() => {
    if (!isReady || firedRef.current) return;
    firedRef.current = true;
    track(
      ANALYTICS_EVENTS.INBOX_VIEWED,
      buildInboxViewedProperties({
        visibleReports: reports,
        totalCount,
        filters: {
          surface: "desktop",
          sourceProductFilter,
          priorityFilter,
          searchQuery,
          scope,
          reportStateFilter,
          defaultReportStateFilter,
        },
      }),
    );
  }, [
    reports,
    totalCount,
    isReady,
    sourceProductFilter,
    priorityFilter,
    searchQuery,
    scope,
    reportStateFilter,
    defaultReportStateFilter,
  ]);
}
