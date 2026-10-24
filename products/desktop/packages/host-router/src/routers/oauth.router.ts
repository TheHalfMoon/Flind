import { OAUTH_SERVICE } from "@flind/core/oauth/identifiers";
import type { OAuthService } from "@flind/core/oauth/oauth";
import { cancelFlowOutput } from "@flind/core/oauth/schemas";
import { publicProcedure, router } from "@flind/host-trpc/trpc";

export const oauthRouter = router({
  cancelFlow: publicProcedure
    .output(cancelFlowOutput)
    .mutation(({ ctx }) =>
      ctx.container.get<OAuthService>(OAUTH_SERVICE).cancelFlow(),
    ),
});
