import { publicProcedure, router } from "@flind/host-trpc/trpc";
import { RELEASE_FEED_SERVICE } from "@flind/workspace-server/services/release-feed/identifiers";
import type { ReleaseFeedService } from "@flind/workspace-server/services/release-feed/release-feed";
import {
  listReleasesInput,
  listReleasesOutput,
} from "@flind/workspace-server/services/release-feed/schemas";

export const releaseFeedRouter = router({
  list: publicProcedure
    .input(listReleasesInput)
    .output(listReleasesOutput)
    .query(({ ctx, input }) =>
      ctx.container
        .get<ReleaseFeedService>(RELEASE_FEED_SERVICE)
        .listReleases(input?.expectVersion),
    ),
});
