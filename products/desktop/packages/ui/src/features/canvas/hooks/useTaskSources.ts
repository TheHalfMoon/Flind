import { taskSources } from "@flind/core/canvas/channelItems";
import { useTasks } from "@flind/ui/features/tasks/useTasks";
import { useMemo } from "react";

/** The sources of the user's recent tasks, so a source filter can offer the sources it hides. */
export function useTaskSources(): string[] {
  const { data: tasks = [] } = useTasks();
  return useMemo(() => taskSources(tasks), [tasks]);
}
