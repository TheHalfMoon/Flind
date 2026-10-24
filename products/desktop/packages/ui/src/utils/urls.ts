import type { CloudRegion } from "@flind/shared";
import {
  flindCloudAppPath,
  verifyFlindExternalLink,
} from "@flind/ui/shell/flindExternalLinks";

/**
 * Compatibility-named UI navigation helper. Never infer host ownership from
 * an inherited region or trust absolute URLs received from server payloads.
 * All navigation remains on the independently configured Flind cloud app.
 */
export function getPostHogUrl(
  pathOrUrl: string,
  _regionOverride?: CloudRegion | null,
): string | null {
  const root = flindCloudAppPath("/");
  if (!root) return null;
  if (/^https?:\/\//i.test(pathOrUrl)) {
    const verified = verifyFlindExternalLink(
      "website",
      new URL(root).hostname,
      { website: pathOrUrl },
    );
    return verified && new URL(verified).origin === new URL(root).origin
      ? verified
      : null;
  }
  if (/^[a-z][a-z0-9+.-]*:/i.test(pathOrUrl)) return null;
  return flindCloudAppPath(
    pathOrUrl.startsWith("/") ? pathOrUrl : "/" + pathOrUrl,
  );
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
