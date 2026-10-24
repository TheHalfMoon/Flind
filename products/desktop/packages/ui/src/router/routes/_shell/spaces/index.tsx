import { SpacesIndex } from "@flind/ui/features/canvas/components/SpacesIndex";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/_shell/spaces/")({
  component: SpacesIndex,
});
