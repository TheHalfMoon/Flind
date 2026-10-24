import { Plus } from "@phosphor-icons/react";
import { Badge } from "@flind/quill";
import { SHORTCUTS } from "@flind/ui/features/command/keyboard-shortcuts";
import { isContentEmpty } from "@flind/ui/features/message-editor/content";
import { useDraftStore } from "@flind/ui/features/message-editor/draftStore";
import { isTaskInputSessionId } from "@flind/ui/features/task-detail/taskInputSession";
import type { MouseEventHandler } from "react";
import { SidebarItem } from "../SidebarItem";
import { SidebarKbdHint } from "./SidebarKbdHint";

interface NewTaskItemProps {
  isActive: boolean;
  onClick: MouseEventHandler<Element>;
}

export function NewTaskItem({ isActive, onClick }: NewTaskItemProps) {
  const hasDraft = useDraftStore((state) =>
    Object.entries(state.drafts).some(
      ([sessionId, draft]) =>
        isTaskInputSessionId(sessionId) && !isContentEmpty(draft),
    ),
  );
  return (
    <SidebarItem
      depth={0}
      icon={<Plus size={16} weight={isActive ? "bold" : "regular"} />}
      label="New task"
      isActive={isActive}
      onClick={onClick}
      endContent={
        hasDraft ? (
          <Badge variant="default" title="You have unsubmitted changes">
            Draft
          </Badge>
        ) : null
      }
      endHint={<SidebarKbdHint keys={SHORTCUTS.NEW_TASK} />}
    />
  );
}
