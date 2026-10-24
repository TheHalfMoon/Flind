import { deriveSessionViewState } from "@flind/core/sessions/sessionViewState";
import type { Task } from "@flind/shared/domain-types";
import {
  useSessionForTask,
  useSessionStore,
} from "@flind/ui/features/sessions/sessionStore";
import { useCwd } from "@flind/ui/features/sidebar/useCwd";
import { useIsCloudTask } from "@flind/ui/features/workspace/useIsCloudTask";
import { useWorkspace } from "@flind/ui/features/workspace/useWorkspace";

export function useSessionViewState(taskId: string, task: Task) {
  const session = useSessionForTask(taskId);
  const repoPath = useCwd(taskId) ?? null;
  const workspace = useWorkspace(taskId);
  const taskIsCloud = useIsCloudTask(taskId, task);
  const isTaskStarting = useSessionStore(
    (state) => state.startingTaskIds[taskId] !== undefined,
  );

  const derived = deriveSessionViewState(
    session,
    task,
    workspace,
    taskIsCloud,
    isTaskStarting,
  );

  return {
    session,
    repoPath,
    ...derived,
  };
}
