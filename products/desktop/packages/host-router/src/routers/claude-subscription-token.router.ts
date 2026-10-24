import {
  CLAUDE_SUBSCRIPTION_TOKEN_STORE,
  type ClaudeSubscriptionTokenStore,
} from "@flind/core/cloud-task/identifiers";
import { publicProcedure, router } from "@flind/host-trpc/trpc";
import { claudeSubscriptionTokenInput } from "@flind/workspace-server/services/claude-subscription/schemas";

export const claudeSubscriptionTokenRouter = router({
  has: publicProcedure.query(({ ctx }) =>
    ctx.container
      .get<ClaudeSubscriptionTokenStore>(CLAUDE_SUBSCRIPTION_TOKEN_STORE)
      .has(),
  ),
  save: publicProcedure
    .input(claudeSubscriptionTokenInput)
    .mutation(({ ctx, input }) =>
      ctx.container
        .get<ClaudeSubscriptionTokenStore>(CLAUDE_SUBSCRIPTION_TOKEN_STORE)
        .save(input.token),
    ),
  clear: publicProcedure.mutation(({ ctx }) =>
    ctx.container
      .get<ClaudeSubscriptionTokenStore>(CLAUDE_SUBSCRIPTION_TOKEN_STORE)
      .clear(),
  ),
});
