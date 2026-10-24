import { CommandCenterView } from "@flind/ui/features/command-center/components/CommandCenterView";
import {
  AppPageSkeleton,
  withRouteSkeleton,
} from "@flind/ui/router/routeSkeletons";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/_shell/command-center")({
  component: CommandCenterView,
  ...withRouteSkeleton(AppPageSkeleton),
});
