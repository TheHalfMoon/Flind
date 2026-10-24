import {
  deriveTaskRunState,
  narrowFullTask,
  type TaskSession,
} from "@flind/core/sidebar/buildSidebarData";
import type { Task } from "@flind/shared/domain-types";
import type { BulkSessionInfo } from "@flind/ui/features/sidebar/useSidebarBulkActions";
import { useSidebarSessionMap } from "@flind/ui/features/sidebar/useSidebarSessionMap";
import { useMemo } from "react";

/**
 * Run state for a list of sessions — enough for a bulk action to know what
 * archiving would stop. Deliberately not the full `TaskData`: that would pull in
 * the workspace and pin queries for a warning sentence.
 */
export function useChannelTasksRunState(tasks: Task[]): BulkSessionInfo[] {
  const sessions = useSidebarSessionMap();

  return useMemo(
    () =>
      tasks.map((task) =>
        deriveTaskRunState(
          narrowFullTask(task),
          sessions.get(task.id) as TaskSession | undefined,
        ),
      ),
    [tasks, sessions],
  );
}
