import { useTaskViewed } from "@flind/ui/features/sidebar/useTaskViewed";
import { useEffect } from "react";

export function useMarkTaskViewed(taskId: string): void {
  const { markAsViewed } = useTaskViewed();

  useEffect(() => {
    markAsViewed(taskId);
  }, [markAsViewed, taskId]);
}
