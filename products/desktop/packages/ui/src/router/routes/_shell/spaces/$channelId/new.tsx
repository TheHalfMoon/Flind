import { SpaceNewTask } from "@flind/ui/features/canvas/components/SpaceNewTask";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/_shell/spaces/$channelId/new")({
  component: NewTaskRoute,
});

function NewTaskRoute() {
  const { channelId } = Route.useParams();
  return <SpaceNewTask channelId={channelId} />;
}
