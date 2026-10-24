import { CANVAS_TEMPLATES_SERVICE } from "@flind/core/canvas/identifiers";
import type { ICanvasTemplatesService } from "@flind/core/canvas/services";
import { canvasTemplateSummarySchema } from "@flind/core/canvas/templateSchemas";
import { publicProcedure, router } from "@flind/host-trpc/trpc";
import { z } from "zod";

export const canvasTemplatesRouter = router({
  list: publicProcedure
    .output(z.array(canvasTemplateSummarySchema))
    .query(({ ctx }) =>
      ctx.container
        .get<ICanvasTemplatesService>(CANVAS_TEMPLATES_SERVICE)
        .list(),
    ),
});
