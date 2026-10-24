import { useService } from "@flind/di/react";
import { useHostTRPC } from "@flind/host-router/react";
import { useOptionalAuthenticatedClient } from "@flind/ui/features/auth/authClient";
import { useAuthStateValue } from "@flind/ui/features/auth/store";
import {
  BROWSER_TABS_CLIENT,
  type BrowserTabsClient,
} from "@flind/ui/features/browser-tabs/browserTabsClient";
import { focusOrOpenBrowserTab } from "@flind/ui/features/browser-tabs/imperativeTabNavigation";
import { useOpenInboxReport } from "@flind/ui/features/inbox/hooks/useOpenInboxReport";
import { navigateToInbox } from "@flind/ui/router/navigationBridge";
import { useQuery } from "@tanstack/react-query";
import { useSubscription } from "@trpc/tanstack-react-query";
import { useCallback, useEffect } from "react";

/**
 * Hook that subscribes to inbox report deep link events (`<scheme>://inbox/{reportId}`,
 * e.g. `posthog-code://…` in production and `posthog-code-dev://…` in local dev)
 * and opens the report in the inbox view. A link with no report segment
 * (`<scheme>://inbox`) opens the inbox itself.
 *
 * The actual open – fetch by id, seed the detail cache, reset filters, and
 * navigate to the right tab (Pulls if it has an implementation PR, otherwise
 * Reports) – lives in {@link useOpenInboxReport}, shared with other in-app
 * surfaces that link to a report by id. On 404/403 (wrong team / deleted /
 * suppressed) it toasts and leaves the current view untouched.
 */
export function useInboxDeepLink() {
  const trpcReact = useHostTRPC();
  const client = useOptionalAuthenticatedClient();
  const tabsClient = useService<BrowserTabsClient>(BROWSER_TABS_CLIENT);
  const isAuthenticated = useAuthStateValue(
    (s) => s.status === "authenticated",
  );

  const openReport = useOpenInboxReport();
  const open = useCallback(
    (reportId: string | null): void => {
      if (reportId) {
        void openReport(reportId, { preserveSource: false, newTab: true });
      } else {
        void focusOrOpenBrowserTab(tabsClient, { href: "/inbox" }).then(
          (handled) => {
            if (handled) return;
            navigateToInbox();
          },
        );
      }
    },
    [openReport, tabsClient],
  );

  const pendingDeepLink = useQuery(
    trpcReact.deepLink.getPendingReportLink.queryOptions(undefined, {
      enabled: isAuthenticated && !!client,
      // Drain once per session – the main process clears its pending entry on read.
      staleTime: Number.POSITIVE_INFINITY,
      refetchOnWindowFocus: false,
      refetchOnReconnect: false,
    }),
  );

  useEffect(() => {
    if (pendingDeepLink.data) {
      open(pendingDeepLink.data.reportId);
    }
  }, [pendingDeepLink.data, open]);

  useSubscription(
    trpcReact.deepLink.onOpenReport.subscriptionOptions(undefined, {
      onData: (data) => {
        if (data) open(data.reportId);
      },
    }),
  );
}
