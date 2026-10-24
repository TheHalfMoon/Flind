import { ActivityFeedList } from "@flind/ui/features/canvas/components/ActivityFeedList";
import { openActivityItem } from "@flind/ui/features/canvas/components/openActivityItem";
import { closeWorkActivity } from "@flind/ui/features/canvas/stores/workActivityStore";

export function WorkActivityColumn({ className }: { className?: string }) {
  return (
    <ActivityFeedList
      className={className}
      onActivate={(item) => {
        openActivityItem(item);
        closeWorkActivity();
      }}
      onOpened={closeWorkActivity}
    />
  );
}
