import { PullRequestsTab } from "@flind/ui/features/inbox/components/PullRequestsTab";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/inbox/pulls/")({
  component: PullRequestsTab,
});
