import {
  useProjectTaskFeeds,
  useProjectTaskFeedsReady,
} from "@flind/ui/features/canvas/hooks/useProjectTaskFeeds";
import {
  ChannelSkeleton,
  withRouteSkeleton,
} from "@flind/ui/router/routeSkeletons";
import { createFileRoute, Navigate } from "@tanstack/react-router";

export const Route = createFileRoute("/_shell/feeds/")({
  component: SavedSearchesIndexRoute,
  ...withRouteSkeleton(ChannelSkeleton),
});

function SavedSearchesIndexRoute() {
  const feeds = useProjectTaskFeeds();
  const ready = useProjectTaskFeedsReady();
  const firstFeedId = feeds[0]?.id;
  if (!ready) return <ChannelSkeleton />;
  if (firstFeedId) {
    return (
      <Navigate replace to="/feeds/$feedId" params={{ feedId: firstFeedId }} />
    );
  }
  return <Navigate replace to="/spaces" />;
}
