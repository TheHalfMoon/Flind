import { resolveServiceOptional } from "@flind/di/container";
import {
  DISK_CACHE_IMAGES,
  type IDiskCacheImages,
} from "@flind/platform/disk-cache";

export function cachedImageUrl(remoteUrl: string): string {
  return (
    resolveServiceOptional<IDiskCacheImages>(DISK_CACHE_IMAGES)?.imageUrl(
      remoteUrl,
    ) ?? remoteUrl
  );
}
