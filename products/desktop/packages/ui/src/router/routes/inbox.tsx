import { InboxView } from "@flind/ui/features/inbox/components/InboxView";
import {
  AppPageSkeleton,
  withRouteSkeleton,
} from "@flind/ui/router/routeSkeletons";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/inbox")({
  component: InboxView,
  ...withRouteSkeleton(AppPageSkeleton),
});
