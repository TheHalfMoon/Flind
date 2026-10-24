import { WebsiteChannelHome } from "@flind/ui/features/canvas/components/WebsiteChannelHome";
import { SpaceTabbedPage } from "@flind/ui/features/canvas/components/work/SpaceTabbedPage";
import { useWorkLayout } from "@flind/ui/features/canvas/hooks/useWorkLayout";
import {
  SpaceActivitySkeleton,
  spaceRouteSkeleton,
  withRouteSkeleton,
} from "@flind/ui/router/routeSkeletons";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/_shell/spaces/$channelId/")({
  component: ChannelHomeRoute,
  ...withRouteSkeleton(spaceRouteSkeleton(SpaceActivitySkeleton)),
});

function ChannelHomeRoute() {
  const { channelId } = Route.useParams();
  if (useWorkLayout()) {
    return (
      <SpaceTabbedPage channelId={channelId} tab="activity">
        <WebsiteChannelHome channelId={channelId} variant="work" />
      </SpaceTabbedPage>
    );
  }
  return <WebsiteChannelHome channelId={channelId} />;
}
