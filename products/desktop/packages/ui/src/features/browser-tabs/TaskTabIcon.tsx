import { CodeIcon } from "@phosphor-icons/react";
import type { Task } from "@flind/shared/domain-types";
import { useChannelTaskData } from "@flind/ui/features/canvas/hooks/useChannelTaskData";
import { TaskIcon } from "@flind/ui/features/sidebar/components/items/TaskIcon";
import { useTaskPrStatus } from "@flind/ui/features/sidebar/useTaskPrStatus";
import { useWorkspace } from "@flind/ui/features/workspace/useWorkspace";

/**
 * The same status icon the Channels sidebar shows for a task (cloud run status,
 * PR state, generating / unread / pinned, needs-permission, …), reused for a
 * task tab so a tab and its sidebar row never drift on icon fidelity. Falls back
 * to a neutral code icon until the task / its data loads.
 */
export function TaskTabIcon({
  task,
  size = 14,
  showPrState = true,
}: {
  task: Task | undefined;
  size?: number;
  showPrState?: boolean;
}) {
  const taskData = useChannelTaskData(task);
  const workspace = useWorkspace(task?.id);
  const workspaceMode =
    workspace?.mode ??
    (taskData?.taskRunEnvironment === "cloud" ? "cloud" : undefined);
  const { prState, hasDiff } = useTaskPrStatus({
    id: task?.id ?? "",
    cloudPrUrl: taskData?.cloudPrUrl ?? null,
    taskRunEnvironment: taskData?.taskRunEnvironment ?? null,
  });

  if (!taskData) {
    return <CodeIcon size={size} className="text-gray-9" />;
  }
  return (
    <TaskIcon
      workspaceMode={workspaceMode}
      isGenerating={taskData.isGenerating}
      isUnread={taskData.isUnread}
      isPinned={taskData.isPinned}
      isSuspended={taskData.isSuspended}
      needsPermission={taskData.needsPermission}
      taskRunStatus={taskData.taskRunStatus}
      runMode={taskData.runMode}
      originProduct={taskData.originProduct}
      slackThreadUrl={taskData.slackThreadUrl}
      prState={showPrState ? prState : null}
      hasDiff={showPrState ? hasDiff : false}
      size={size}
    />
  );
}
