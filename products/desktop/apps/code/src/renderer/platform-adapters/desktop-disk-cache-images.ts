import type { IDiskCacheImages } from "@flind/platform/disk-cache";
import {
  isCacheableImageUrl,
  toCachedImageUrl,
} from "@shared/disk-cache-protocol";

export const desktopDiskCacheImages: IDiskCacheImages = {
  imageUrl: (remoteUrl) =>
    isCacheableImageUrl(remoteUrl) ? toCachedImageUrl(remoteUrl) : remoteUrl,
};
