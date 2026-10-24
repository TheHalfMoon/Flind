import { SLACK_INTEGRATION_SERVICE } from "@flind/core/integrations/identifiers";
import {
  startIntegrationFlowInput,
  startIntegrationFlowOutput,
} from "@flind/core/integrations/schemas";
import {
  type SlackIntegrationCallback,
  SlackIntegrationEvent,
  type SlackIntegrationService,
} from "@flind/core/integrations/slack";
import { publicProcedure, router } from "@flind/host-trpc/trpc";

export const slackIntegrationRouter = router({
  startFlow: publicProcedure
    .input(startIntegrationFlowInput)
    .output(startIntegrationFlowOutput)
    .mutation(({ ctx, input }) => {
      return ctx.container
        .get<SlackIntegrationService>(SLACK_INTEGRATION_SERVICE)
        .startFlow(input.region, input.projectId);
    }),

  onCallback: publicProcedure.subscription(async function* (opts) {
    const service = opts.ctx.container.get<SlackIntegrationService>(
      SLACK_INTEGRATION_SERVICE,
    );
    const iterable = service.toIterable(SlackIntegrationEvent.Callback, {
      signal: opts.signal,
    });
    for await (const data of iterable) {
      yield data;
    }
  }),

  onFlowTimedOut: publicProcedure.subscription(async function* (opts) {
    const service = opts.ctx.container.get<SlackIntegrationService>(
      SLACK_INTEGRATION_SERVICE,
    );
    const iterable = service.toIterable(SlackIntegrationEvent.FlowTimedOut, {
      signal: opts.signal,
    });
    for await (const data of iterable) {
      yield data;
    }
  }),

  consumePendingCallback: publicProcedure.query(
    ({ ctx }): SlackIntegrationCallback | null =>
      ctx.container
        .get<SlackIntegrationService>(SLACK_INTEGRATION_SERVICE)
        .consumePendingCallback(),
  ),
});
