import { WebsiteChannelHistory } from "@flind/ui/features/canvas/components/WebsiteChannelHistory";
import {
  ChannelSkeleton,
  withRouteSkeleton,
} from "@flind/ui/router/routeSkeletons";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/_shell/spaces/$channelId/history")({
  component: ChannelHistoryRoute,
  ...withRouteSkeleton(ChannelSkeleton),
});

function ChannelHistoryRoute() {
  const { channelId } = Route.useParams();
  return <WebsiteChannelHistory channelId={channelId} />;
}
