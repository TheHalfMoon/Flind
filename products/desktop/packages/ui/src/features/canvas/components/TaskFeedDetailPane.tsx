import { MagnifyingGlassIcon } from "@phosphor-icons/react";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@flind/quill";
import { useChannels } from "@flind/ui/features/canvas/hooks/useChannels";
import { useTaskFeedSelection } from "@flind/ui/features/canvas/stores/taskFeedSelectionStore";
import { OpenSidebarButton } from "@flind/ui/features/sidebar/components/OpenSidebarButton";
import { TaskDetail } from "@flind/ui/features/task-detail/components/TaskDetail";
import { useResolvedTask } from "@flind/ui/features/tasks/useResolvedTask";
import { TaskDetailSkeleton } from "@flind/ui/router/routeSkeletons";

export function TaskFeedDetailPane({
  feedId,
  routeTaskId,
}: {
  feedId: string;
  /** The task named by the URL, when the location carries one. */
  routeTaskId?: string;
}) {
  const selected = useTaskFeedSelection(feedId);
  // The URL wins: a location that names a task shows it, even in a fresh tab
  // or after a reload where the in-memory selection is empty.
  const taskId = routeTaskId ?? selected?.taskId;
  const task = useResolvedTask(taskId);
  const { channels } = useChannels();

  if (!taskId) {
    return (
      <div className="flex h-full items-center justify-center">
        <Empty className="border-0">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <MagnifyingGlassIcon />
            </EmptyMedia>
            <EmptyTitle>Nothing selected</EmptyTitle>
            <EmptyDescription>
              Pick a task from the search to read it here.
            </EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <OpenSidebarButton />
          </EmptyContent>
        </Empty>
      </div>
    );
  }

  if (!task) return <TaskDetailSkeleton />;

  const channelId = task.channel ?? selected?.channelId ?? undefined;
  const channelName = channels.find((c) => c.id === channelId)?.name;

  return (
    <div className="h-full min-w-0">
      <TaskDetail
        task={task}
        channelName={channelName}
        channelId={channelName ? channelId : undefined}
      />
    </div>
  );
}
