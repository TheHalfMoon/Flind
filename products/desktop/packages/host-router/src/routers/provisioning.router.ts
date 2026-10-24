import { PROVISIONING_SERVICE } from "@flind/core/provisioning/identifiers";
import {
  ProvisioningEvent,
  type ProvisioningService,
} from "@flind/core/provisioning/provisioning";
import { publicProcedure, router } from "@flind/host-trpc/trpc";

export const provisioningRouter = router({
  onOutput: publicProcedure.subscription(async function* (opts) {
    const service =
      opts.ctx.container.get<ProvisioningService>(PROVISIONING_SERVICE);
    for await (const data of service.toIterable(ProvisioningEvent.Output, {
      signal: opts.signal,
    })) {
      yield data;
    }
  }),
});
