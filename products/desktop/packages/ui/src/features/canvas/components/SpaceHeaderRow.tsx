import type { Task } from "@flind/shared/domain-types";
import { ActivityDetailCloseButton } from "@flind/ui/features/canvas/components/ActivityDetailCloseButton";
import { useActivitySelection } from "@flind/ui/features/canvas/stores/activityDetailStore";
import { useActiveTabTiled } from "@flind/ui/features/tab-tiling/useActiveTabTiled";
import { TaskHeaderActions } from "@flind/ui/features/task-detail/components/TaskHeaderActions";
import { ChromeBar } from "@flind/ui/primitives/ChromeBar";
import { useHeaderStore } from "@flind/ui/shell/headerStore";

/**
 * The title row above the content pane. Subscribes to the header store itself:
 * the layout renders the screen that writes that store, so subscribing up there
 * makes every title write re-render the writer.
 */
export function SpaceHeaderRow({ task }: { task?: Task }) {
  const content = useHeaderStore((s) => s.content);
  const activitySelection = useActivitySelection();
  const tiled = useActiveTabTiled();
  const showsActivitySession = activitySelection?.kind === "task";
  if (tiled || (!content && !task && !showsActivitySession)) return null;

  return (
    <ChromeBar inset="title">
      <div className="flex h-full min-w-0 flex-1 items-center justify-between overflow-hidden">
        {content}
      </div>
      {/* Rendered without a wrapper: the actions cap themselves at half the
          bar, and a wrapper that hugs their content resolves that percentage
          against itself, which clips them. */}
      {task && <TaskHeaderActions task={task} />}
      {showsActivitySession && <ActivityDetailCloseButton />}
    </ChromeBar>
  );
}
