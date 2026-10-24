import { RunsTab } from "@flind/ui/features/inbox/components/RunsTab";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/inbox/runs/")({
  component: RunsTab,
});
