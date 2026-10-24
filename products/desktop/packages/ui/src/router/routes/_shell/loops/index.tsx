import { LoopsListView } from "@flind/ui/features/loops/components/LoopsListView";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/_shell/loops/")({
  component: LoopsListView,
});
