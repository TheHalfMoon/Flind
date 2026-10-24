import { type CloudRegion, getCloudUrlFromRegion } from "@flind/shared";

export function buildPostHogUrl(
  pathOrUrl: string,
  region: CloudRegion | null,
): string | null {
  if (/^https?:\/\//i.test(pathOrUrl)) return pathOrUrl;
  if (!region) return null;
  const base = getCloudUrlFromRegion(region);
  return `${base}${pathOrUrl.startsWith("/") ? pathOrUrl : `/${pathOrUrl}`}`;
}
