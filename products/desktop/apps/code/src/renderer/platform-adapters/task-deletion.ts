import type {
  ITaskDeletionHost,
  ITaskDeletionWorkspaceClient,
  TaskDeletionFocusSession,
  TaskDeletionView,
  TaskWorkspace,
} from "@flind/core/tasks/identifiers";
import { useFocusStore } from "@flind/ui/features/focus/focusStore";
import { pinnedTasksApi } from "@flind/ui/features/sidebar/taskMetaApi";
import { getAppViewSnapshot } from "@flind/ui/router/useAppView";
import { openTaskInput } from "@flind/ui/router/useOpenTask";
import { trpcClient } from "@renderer/trpc/client";

export const taskDeletionWorkspaceClient: ITaskDeletionWorkspaceClient = {
  getAll() {
    return trpcClient.workspace.getAll.query() as Promise<
      Record<string, TaskWorkspace>
    >;
  },
  delete(input) {
    return trpcClient.workspace.delete.mutate(input);
  },
};

export const taskDeletionHost: ITaskDeletionHost = {
  getSession(): TaskDeletionFocusSession | null {
    return useFocusStore.getState().session;
  },
  disableFocus() {
    return useFocusStore.getState().disableFocus();
  },
  confirmDeleteTask(input) {
    return trpcClient.contextMenu.confirmDeleteTask.mutate(input);
  },
  unpin(taskId) {
    return pinnedTasksApi.unpin(taskId);
  },
  getCurrentView(): TaskDeletionView | undefined {
    const view = getAppViewSnapshot();
    return {
      type: view.type,
      data: view.taskId ? { id: view.taskId } : null,
    } as TaskDeletionView;
  },
  navigateToTaskInput() {
    openTaskInput();
  },
};
