import { redirectFromLegacyPath } from "@flind/ui/router/legacyPaths";
import { createFileRoute } from "@tanstack/react-router";

// `/code` itself, which was the new-task screen. See code.$.tsx.
export const Route = createFileRoute("/code/")({
  beforeLoad: ({ location }) => redirectFromLegacyPath(location),
});
