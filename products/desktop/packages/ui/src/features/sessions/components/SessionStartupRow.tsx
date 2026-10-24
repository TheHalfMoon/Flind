import type { Task } from "@flind/shared/domain-types";
import { useProvisioningStore } from "@flind/ui/features/provisioning/store";
import { SessionProvisioningStatus } from "@flind/ui/features/sessions/components/SessionProvisioningStatus";
import {
  SessionStartupStatus,
  startupLabel,
} from "@flind/ui/features/sessions/components/SessionStartupStatus";
import { useSessionViewState } from "@flind/ui/features/sessions/hooks/useSessionViewState";
import { useSessionStore } from "@flind/ui/features/sessions/sessionStore";

export function SessionStartupRow({
  taskId,
  task,
  hasCurrentSetupProgress,
}: {
  taskId: string;
  task: Task;
  hasCurrentSetupProgress: boolean;
}) {
  const isProvisioning = useProvisioningStore((s) => s.activeTasks.has(taskId));
  const startupPhase = useSessionStore(
    (state) => state.startingTaskIds[taskId]?.phase,
  );
  const { isCloud, isRunning, isInitializing, hasError } = useSessionViewState(
    taskId,
    task,
  );
  const executionTarget = isCloud ? "cloud" : "local";

  if (isProvisioning) {
    return (
      <SessionProvisioningStatus
        executionTarget={executionTarget}
        taskId={taskId}
      />
    );
  }
  if (hasCurrentSetupProgress || hasError || (isRunning && !isInitializing)) {
    return null;
  }
  return (
    <SessionStartupStatus
      label={
        isInitializing
          ? startupLabel(executionTarget, startupPhase)
          : "Connecting to agent..."
      }
    />
  );
}
