import { BellIcon } from "@phosphor-icons/react";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@flind/quill";
import { ActivityDetailCloseButton } from "@flind/ui/features/canvas/components/ActivityDetailCloseButton";
import { useChannels } from "@flind/ui/features/canvas/hooks/useChannels";
import { useInboxActivityPreview } from "@flind/ui/features/canvas/hooks/useInboxActivityPreview";
import { useActivitySelection } from "@flind/ui/features/canvas/stores/activityDetailStore";
import { ReportDetail } from "@flind/ui/features/inbox/components/ReportDetail";
import { OpenSidebarButton } from "@flind/ui/features/sidebar/components/OpenSidebarButton";
import { TaskDetail } from "@flind/ui/features/task-detail/components/TaskDetail";
import { useResolvedTask } from "@flind/ui/features/tasks/useResolvedTask";
import { TaskDetailSkeleton } from "@flind/ui/router/routeSkeletons";

/** What the Activity destination shows beside its feed. */
export function ActivityDetailPane() {
  const selected = useActivitySelection();
  const selectedTaskId =
    selected?.kind === "task" ? selected.taskId : undefined;
  const task = useResolvedTask(selectedTaskId);
  const { channels } = useChannels();
  const { reports } = useInboxActivityPreview();

  if (!selected) {
    return (
      <div className="flex h-full items-center justify-center">
        <Empty className="border-0">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <BellIcon />
            </EmptyMedia>
            <EmptyTitle>Nothing selected</EmptyTitle>
            <EmptyDescription>
              Pick something from the feed to read it here.
            </EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <OpenSidebarButton />
          </EmptyContent>
        </Empty>
      </div>
    );
  }

  if (selected.kind === "report") {
    const cachedReport = reports.find(
      (report) => report.id === selected.reportId,
    );
    return (
      <div className="h-full min-w-0">
        <ReportDetail
          reportId={selected.reportId}
          cachedReport={cachedReport}
          backTo="/activity"
          backLabel="Back to activity"
          statusRedirect={false}
          headerTrailingAction={<ActivityDetailCloseButton />}
        />
      </div>
    );
  }

  if (!task) return <TaskDetailSkeleton />;

  const { channelId } = selected;
  const channelName = channels.find((c) => c.id === channelId)?.name;

  return (
    <div className="h-full min-w-0">
      <TaskDetail
        task={task}
        channelName={channelName ?? "Space"}
        channelId={channelId ?? undefined}
      />
    </div>
  );
}
