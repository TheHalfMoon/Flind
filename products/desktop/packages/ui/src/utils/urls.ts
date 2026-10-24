import { type CloudRegion, getCloudUrlFromRegion } from "@flind/shared";
import { useAuthStore } from "@flind/ui/features/auth/store";
import { verifyFlindExternalLink } from "@flind/ui/shell/flindExternalLinks";

export function getPostHogUrl(
  pathOrUrl: string,
  regionOverride?: CloudRegion | null,
): string | null {
  if (/^https?:\/\//i.test(pathOrUrl)) return pathOrUrl;
  const region =
    regionOverride ?? useAuthStore.getState().authState.cloudRegion;
  if (!region) return null;
  const base = getCloudUrlFromRegion(region);
  return `${base}${pathOrUrl.startsWith("/") ? pathOrUrl : `/${pathOrUrl}`}`;
}

/** A Flind payment URL must be explicitly provisioned and verified.
 * Never build an inherited provider billing/legacy SKU route. */
export function getBillingUrl(
  _regionOverride?: CloudRegion | null,
): string | null {
  return verifyFlindExternalLink(
    "website",
    import.meta.env.VITE_FLIND_CLOUD_APP_HOST,
    { website: import.meta.env.VITE_FLIND_BILLING_URL },
  );
}
