import { INTEGRATION_SERVICE } from "@flind/core/integrations/identifiers";
import type { IntegrationService } from "@flind/core/integrations/integration";
import {
  startGenericIntegrationFlowInput,
  startIntegrationFlowOutput,
} from "@flind/core/integrations/schemas";
import { publicProcedure, router } from "@flind/host-trpc/trpc";

/**
 * Generic OAuth integration flow starter, parameterized by `kind`. Replaces the need for a
 * per-provider router when adding a new OAuth data source — the source's connect-form schema
 * already carries the `kind`, so the UI passes it straight through.
 */
export const integrationRouter = router({
  startFlow: publicProcedure
    .input(startGenericIntegrationFlowInput)
    .output(startIntegrationFlowOutput)
    .mutation(({ ctx, input }) => {
      return ctx.container
        .get<IntegrationService>(INTEGRATION_SERVICE)
        .startFlow(input.kind, input.region, input.projectId);
    }),
});
