import { publicProcedure, router } from "@flind/host-trpc/trpc";
import {
  DISK_CACHE_SERVICE,
  type IDiskCache,
} from "@flind/platform/disk-cache";

export const diskCacheRouter = router({
  clear: publicProcedure.mutation(({ ctx }) =>
    ctx.container.get<IDiskCache>(DISK_CACHE_SERVICE).clear(),
  ),
});
