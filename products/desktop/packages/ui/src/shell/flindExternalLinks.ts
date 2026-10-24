/**
 * Public marketing/legal destinations are opt-in. They are never inferred
 * from the inherited provider or from a URL supplied by an untrusted user.
 */
export type FlindExternalDestination =
  | "support"
  | "community"
  | "docs"
  | "website"
  | "privacy";

type ConfiguredLinks = Partial<Record<FlindExternalDestination, string>>;

/** Require a first-party HTTPS URL on an EXACT configured hostname. */
export function verifyFlindExternalLink(
  destination: FlindExternalDestination,
  hostname: string | undefined,
  urls: ConfiguredLinks,
): string | null {
  const candidate = urls[destination];
  if (!candidate || !hostname) return null;
  const expected = hostname.trim().toLowerCase();
  if (!expected || expected.includes("/") || expected.includes(":"))
    return null;
  try {
    const parsed = new URL(candidate);
    if (
      parsed.protocol !== "https:" ||
      parsed.hostname.toLowerCase() !== expected ||
      parsed.username ||
      parsed.password ||
      parsed.port ||
      parsed.hash
    ) {
      return null;
    }
    return parsed.href;
  } catch {
    return null;
  }
}

/** Renderer-owned configuration, no provider URLs or invented default host. */
export function flindExternalUrl(
  destination: FlindExternalDestination,
): string | null {
  return verifyFlindExternalLink(
    destination,
    import.meta.env.VITE_FLIND_WEBSITE_HOST,
    {
      support: import.meta.env.VITE_FLIND_SUPPORT_URL,
      community: import.meta.env.VITE_FLIND_COMMUNITY_URL,
      docs: import.meta.env.VITE_FLIND_DOCS_URL,
      website: import.meta.env.VITE_FLIND_WEBSITE_URL,
      privacy: import.meta.env.VITE_FLIND_PRIVACY_URL,
    },
  );
}
