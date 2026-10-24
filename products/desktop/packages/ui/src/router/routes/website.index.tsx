import { redirectFromLegacyPath } from "@flind/ui/router/legacyPaths";
import { createFileRoute } from "@tanstack/react-router";

// `/website` itself, which is now the spaces index. See website.$.tsx.
export const Route = createFileRoute("/website/")({
  beforeLoad: ({ location }) => redirectFromLegacyPath(location),
});
