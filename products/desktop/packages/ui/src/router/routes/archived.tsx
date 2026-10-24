import { ArchivedTasksView } from "@flind/ui/features/archive/ArchivedTasksView";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/archived")({
  component: ArchivedTasksView,
});
