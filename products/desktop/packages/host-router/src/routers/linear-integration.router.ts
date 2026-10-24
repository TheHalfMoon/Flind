import { LINEAR_INTEGRATION_SERVICE } from "@flind/core/integrations/identifiers";
import type { LinearIntegrationService } from "@flind/core/integrations/linear";
import {
  startIntegrationFlowInput,
  startIntegrationFlowOutput,
} from "@flind/core/integrations/schemas";
import { publicProcedure, router } from "@flind/host-trpc/trpc";

export const linearIntegrationRouter = router({
  startFlow: publicProcedure
    .input(startIntegrationFlowInput)
    .output(startIntegrationFlowOutput)
    .mutation(({ ctx, input }) => {
      return ctx.container
        .get<LinearIntegrationService>(LINEAR_INTEGRATION_SERVICE)
        .startFlow(input.region, input.projectId);
    }),
});
