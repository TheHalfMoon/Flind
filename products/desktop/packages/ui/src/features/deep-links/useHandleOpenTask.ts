import {
  type CommentTarget,
  commentScopeFromWire,
} from "@flind/core/comments/anchors";
import type { TaskLinkCommentAnchor } from "@flind/core/links/task-link";
import {
  TASK_SERVICE,
  type TaskService,
} from "@flind/core/task-detail/taskService";
import { useService } from "@flind/di/react";
import type { Task } from "@flind/shared/domain-types";
import { useCommentNavigationStore } from "@flind/ui/features/sessions/commentNavigationStore";
import { useTaskViewed } from "@flind/ui/features/sidebar/useTaskViewed";
import { taskKeys } from "@flind/ui/features/tasks/taskKeys";
import { toast } from "@flind/ui/primitives/toast";
import { openTask as openTaskHelper } from "@flind/ui/router/useOpenTask";
import { logger } from "@flind/ui/shell/logger";
import { useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

const log = logger.scope("open-task");

/**
 * Opens a task from a deep link / notification click, provisioning its
 * workspace via the TASK_SERVICE saga (so it works even when the task isn't
 * loaded yet). Returns a stable callback shared by the task URL-scheme deep link
 * (`useTaskDeepLink`) and the generic notification-target consumer
 * (`useOpenTargetDeepLink`).
 */
function commentTargetFromAnchor(
  taskId: string,
  anchor: TaskLinkCommentAnchor,
): CommentTarget {
  const scope = commentScopeFromWire(anchor.scope);
  if ((scope === "canvas" || scope === "task_artifact") && anchor.itemId) {
    return { scope, itemId: anchor.itemId };
  }
  return { scope: "task", itemId: taskId };
}

export function useHandleOpenTask(): (
  taskId: string,
  taskRunId?: string,
  comment?: TaskLinkCommentAnchor,
) => Promise<void> {
  const taskService = useService<TaskService>(TASK_SERVICE);
  const { markAsViewed } = useTaskViewed();
  const queryClient = useQueryClient();

  return useCallback(
    async (
      taskId: string,
      taskRunId?: string,
      comment?: TaskLinkCommentAnchor,
    ) => {
      log.info(
        `Opening task from deep link: ${taskId}${taskRunId ? `, run: ${taskRunId}` : ""}`,
      );
      try {
        const result = await taskService.openTask(taskId, taskRunId);
        if (!result.success) {
          log.error("Failed to open task from deep link", {
            taskId,
            taskRunId,
            error: result.error,
            failedStep: result.failedStep,
          });
          toast.error(`Failed to open task: ${result.error}`);
          return;
        }

        const { task } = result.data;
        queryClient.setQueryData<Task[]>(taskKeys.list(), (old) => {
          if (!old) return [task];
          const existingIndex = old.findIndex((t) => t.id === task.id);
          if (existingIndex >= 0) {
            const updated = [...old];
            updated[existingIndex] = task;
            return updated;
          }
          return [task, ...old];
        });
        queryClient.invalidateQueries({ queryKey: taskKeys.lists() });

        markAsViewed(taskId);
        const channelTarget = task.channel
          ? { channelId: task.channel, newTab: true }
          : { newTab: true };
        void openTaskHelper(task, channelTarget);
        if (comment) {
          useCommentNavigationStore
            .getState()
            .requestCommentFocus(
              taskId,
              commentTargetFromAnchor(taskId, comment),
              comment.threadId,
            );
        }
        log.info(`Opened task from deep link: ${taskId}`);
      } catch (error) {
        log.error("Unexpected error opening task from deep link:", error);
        toast.error("Failed to open task");
      }
    },
    [markAsViewed, queryClient, taskService],
  );
}
