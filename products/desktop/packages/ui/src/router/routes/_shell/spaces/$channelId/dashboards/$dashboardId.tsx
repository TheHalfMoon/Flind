import { WebsiteDashboard } from "@flind/ui/features/canvas/components/WebsiteDashboard";
import {
  CanvasSkeleton,
  withRouteSkeleton,
} from "@flind/ui/router/routeSkeletons";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute(
  "/_shell/spaces/$channelId/dashboards/$dashboardId",
)({
  component: DashboardRoute,
  ...withRouteSkeleton(CanvasSkeleton),
});

function DashboardRoute() {
  const { dashboardId } = Route.useParams();
  return <WebsiteDashboard dashboardId={dashboardId} />;
}
