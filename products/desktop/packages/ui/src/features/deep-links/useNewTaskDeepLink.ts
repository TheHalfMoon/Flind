import type { NewTaskLinkAnalytics } from "@flind/core/deep-links/identifiers";
import {
  NEW_TASK_LINK_RESOLVER,
  type NewTaskLinkResolver,
} from "@flind/core/deep-links/newTaskLinkResolver";
import { useService } from "@flind/di/react";
import { useHostTRPCClient } from "@flind/host-router/react";
import type { NewTaskLinkPayload } from "@flind/shared";
import { ANALYTICS_EVENTS } from "@flind/shared/analytics-events";
import { useAuthStateValue } from "@flind/ui/features/auth/store";
import { useTaskInputPrefillStore } from "@flind/ui/features/task-detail/stores/taskInputPrefillStore";
import { toast } from "@flind/ui/primitives/toast";
import { openTaskInput } from "@flind/ui/router/useOpenTask";
import { track } from "@flind/ui/shell/analytics";
import { logger } from "@flind/ui/shell/logger";
import { useCallback, useEffect, useRef } from "react";

const log = logger.scope("new-task-deep-link");

function trackResolution(analytics: NewTaskLinkAnalytics) {
  switch (analytics.event) {
    case ANALYTICS_EVENTS.DEEP_LINK_NEW_TASK:
      return track(analytics.event, analytics.properties);
    case ANALYTICS_EVENTS.DEEP_LINK_PLAN:
      return track(analytics.event, analytics.properties);
    case ANALYTICS_EVENTS.DEEP_LINK_ISSUE:
      return track(analytics.event, analytics.properties);
    case ANALYTICS_EVENTS.DEEP_LINK_ISSUE_FAILED:
      return track(analytics.event, analytics.properties);
  }
}

export function useNewTaskDeepLink() {
  const client = useHostTRPCClient();
  const resolver = useService<NewTaskLinkResolver>(NEW_TASK_LINK_RESOLVER);
  const isAuthenticated = useAuthStateValue(
    (state) => state.status === "authenticated",
  );
  const hasFetchedPending = useRef(false);

  const handleAction = useCallback(
    async (payload: NewTaskLinkPayload) => {
      log.info(`Handling deep link action: ${payload.action}`);
      useTaskInputPrefillStore.getState().clearReportAssociation();

      const result = await resolver.resolve(payload);
      trackResolution(result.analytics);

      if (result.kind === "navigate") {
        openTaskInput({ ...result.navigation, newTab: true });
        return;
      }

      toast.error(result.title, { description: result.description });
      log.warn(result.title, result.description);
    },
    [resolver],
  );

  useEffect(() => {
    if (!isAuthenticated) {
      hasFetchedPending.current = false;
      return;
    }
    if (hasFetchedPending.current) return;

    const fetchPending = async () => {
      hasFetchedPending.current = true;
      try {
        const pending = await client.deepLink.getPendingNewTaskLink.query();
        if (pending) {
          log.info(`Found pending new task link: action=${pending.action}`);
          handleAction(pending).catch((error) => {
            log.error("Failed to handle pending new task link:", error);
          });
        }
      } catch (error) {
        hasFetchedPending.current = false;
        log.error("Failed to check for pending new task link:", error);
      }
    };

    fetchPending();
  }, [isAuthenticated, handleAction, client]);

  useEffect(() => {
    const subscription = client.deepLink.onNewTaskAction.subscribe(undefined, {
      onData: (data) => {
        log.info(`Received new task link event: action=${data.action}`);
        handleAction(data).catch((error) => {
          log.error("Failed to handle new task link action:", error);
        });
      },
    });
    return () => subscription.unsubscribe();
  }, [client, handleAction]);
}
