import { useService } from "@flind/di/react";
import { useHostTRPC } from "@flind/host-router/react";
import { useAuthStateValue } from "@flind/ui/features/auth/store";
import {
  BROWSER_TABS_CLIENT,
  type BrowserTabsClient,
} from "@flind/ui/features/browser-tabs/browserTabsClient";
import { focusOrOpenBrowserTab } from "@flind/ui/features/browser-tabs/imperativeTabNavigation";
import { navigateToLoopDetail } from "@flind/ui/router/navigationBridge";
import { useQuery } from "@tanstack/react-query";
import { useSubscription } from "@trpc/tanstack-react-query";
import { useCallback, useEffect } from "react";

export function useLoopDeepLink() {
  const trpcReact = useHostTRPC();
  const tabsClient = useService<BrowserTabsClient>(BROWSER_TABS_CLIENT);
  const isAuthenticated = useAuthStateValue(
    (s) => s.status === "authenticated",
  );

  const pendingDeepLink = useQuery(
    trpcReact.deepLink.getPendingLoopLink.queryOptions(undefined, {
      enabled: isAuthenticated,
      staleTime: Number.POSITIVE_INFINITY,
      refetchOnWindowFocus: false,
      refetchOnReconnect: false,
    }),
  );

  const openLoop = useCallback(
    (loopId: string): void => {
      void focusOrOpenBrowserTab(tabsClient, {
        href: `/loops/${loopId}`,
        appView: "loops",
      }).then((handled) => {
        if (handled) return;
        navigateToLoopDetail(loopId);
      });
    },
    [tabsClient],
  );

  useEffect(() => {
    if (pendingDeepLink.data?.loopId) {
      openLoop(pendingDeepLink.data.loopId);
    }
  }, [pendingDeepLink.data, openLoop]);

  useSubscription(
    trpcReact.deepLink.onOpenLoop.subscriptionOptions(undefined, {
      onData: (data) => {
        if (data?.loopId) openLoop(data.loopId);
      },
    }),
  );
}
