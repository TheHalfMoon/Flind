/**
 * An opt-in desktop telemetry or log destination must be an independently
 * configured HTTPS origin, never an inherited first-party vendor domain.
 * This is URL validation, not proof of domain ownership.
 */
export function flindAnalyticsOrigin(value: string | undefined): string | null {
  if (!value?.trim()) return null;
  try {
    const url = new URL(value.trim());
    const hostname = url.hostname.toLowerCase().replace(/\.$/, "");
    if (
      url.protocol !== "https:" ||
      !hostname ||
      url.username ||
      url.password ||
      url.search ||
      url.hash ||
      url.pathname !== "/" ||
      hostname === "posthog.com" ||
      hostname.endsWith(".posthog.com") ||
      hostname === "posthog.dev" ||
      hostname.endsWith(".posthog.dev")
    ) {
      return null;
    }
    return url.origin;
  } catch {
    return null;
  }
}
