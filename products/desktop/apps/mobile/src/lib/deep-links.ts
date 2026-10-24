/**
 * Deep-link URL construction for the mobile app.
 *
 * Path shape mirrors the desktop app (apps/code/src/shared/deeplink.ts and
 * the registered handlers in main/services/*-link/) so a single URL can route
 * to either client:
 *   flind://task/<taskId>
 *   flind://task/<taskId>/run/<runId>
 *   flind://inbox/<reportId>
 *   flind://inbox/<reportId>/<slug>   (slug is cosmetic, ignored on receive)
 *
 * Mobile uses the flind:// custom scheme (registered in app.json).
 * HTTPS universal-link hosts are disabled until a Flind-owned domain and
 * its OS association files have been verified and configured.
 *
 * For in-app navigation, prefer the `paths.*` helpers — they return the
 * router-relative path that `router.push()` expects. For external/shareable
 * links (push notifications, Slack messages, copy-link buttons), use
 * `universalUrl()` or `customSchemeUrl()`. To produce a human-readable share
 * link for an inbox report, use `inboxReportShareUrl(reportId, title)`.
 */

export const MOBILE_SCHEME = "flind";

/**
 * HTTPS universal links require an explicitly controlled Flind host.
 * Native OS association files must be provisioned separately before release.
 */
export function getUniversalLinkOrigin(): string | null {
  const raw = process.env.EXPO_PUBLIC_FLIND_UNIVERSAL_LINK_ORIGIN;
  if (!raw) return null;
  if (raw.trim() !== raw) {
    throw new Error("Flind universal-link origin must not have whitespace");
  }
  let parsed: URL;
  try {
    parsed = new URL(raw);
  } catch {
    throw new Error("Flind universal-link origin must be an absolute HTTPS origin");
  }
  const hostname = parsed.hostname.toLowerCase().replace(/\.+$/, "");
  if (
    parsed.protocol !== "https:" ||
    !hostname ||
    hostname === "posthog.com" ||
    hostname.endsWith(".posthog.com") ||
    parsed.username ||
    parsed.password ||
    parsed.pathname !== "/" ||
    parsed.search ||
    parsed.hash
  ) {
    throw new Error("Flind universal-link origin must be an approved HTTPS origin");
  }
  return parsed.origin;
}

/**
 * Router-relative paths used inside the app with `router.push()` /
 * `router.replace()`. These are also the path shape that expo-router maps
 * incoming deep links to.
 */
export const paths = {
  tasksTab: "/(tabs)/tasks" as const,
  inboxTab: "/(tabs)/inbox" as const,
  settings: "/settings" as const,
  newTask: "/task" as const,
  task: (taskId: string) => `/task/${taskId}` as const,
  inboxReport: (reportId: string) => `/inbox/${reportId}` as const,
} as const;

/** A path is the part after the host: starts with `/`, no scheme. */
type AppPath = string;

/** Build a shareable `flind://...` URL for an in-app path. */
export function customSchemeUrl(path: AppPath): string {
  const trimmed = path.replace(/^\/+/, "");
  return `${MOBILE_SCHEME}://${trimmed}`;
}

/** Build a shareable HTTPS URL only when a verified Flind origin is configured. */
export function universalUrl(path: AppPath): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  const origin = getUniversalLinkOrigin();
  if (!origin) throw new Error("Flind universal links are not configured");
  return origin + normalized;
}

/**
 * Slugify a free-form title for use as a trailing path segment on a shareable
 * deep link. Mirrors `buildInboxDeeplink`'s slug rules in the desktop app
 * (apps/code/src/shared/deeplink.ts) exactly:
 *
 * - Accented Latin letters are folded to their ASCII base (`café` → `cafe`)
 *   via NFD decomposition + combining-mark stripping.
 * - Letters, digits, and the URL-unreserved punctuation `_ . ~` are kept
 *   verbatim (case preserved).
 * - Any run of other characters collapses to a single `-`, except runs that
 *   mix a colon with other unsafe chars collapse to `--`. This preserves the
 *   title-like break in `fix(inbox): Add foo` → `fix-inbox--Add-foo` while
 *   keeping standalone colons compact (`feat:bar` → `feat-bar`) and unrelated
 *   runs single (`Cost $5, 50% off` → `Cost-5-50-off`).
 * - Leading and trailing hyphens are stripped.
 *
 * Returns the empty string when the input is null/undefined/empty or
 * slugifies to nothing.
 */
export function slugifyTitle(title: string | null | undefined): string {
  if (!title) return "";
  return title
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .replace(/[^a-zA-Z0-9_.~]+/g, (run) =>
      run.includes(":") && /[^:]/.test(run) ? "--" : "-",
    )
    .replace(/^-+|-+$/g, "");
}

/**
 * Build a shareable `flind://inbox/<reportId>` URL, optionally with a
 * cosmetic slug suffix derived from the title. The slug is purely cosmetic;
 * receivers must ignore everything after the UUID. See
 * `externalUrlToAppPath` for the corresponding inbound tolerance.
 */
export function inboxReportShareUrl(
  reportId: string,
  title?: string | null,
): string {
  const slug = slugifyTitle(title);
  const path = slug ? `/inbox/${reportId}/${slug}` : `/inbox/${reportId}`;
  return customSchemeUrl(path);
}

/**
 * Convert an incoming external URL (custom scheme or universal link) to the
 * router-relative path expo-router uses. Returns null if the URL doesn't
 * belong to us.
 *
 * A `flind://inbox/<id>/<slug>` link (or the universal-link equivalent) is
 * normalized to `/inbox/<id>` — the slug is decorative and the route only
 * cares about the UUID. Mirrors the desktop receiver, which also ignores the
 * slug.
 *
 * Used by the auth gate to round-trip the originally-requested URL through
 * the sign-in flow.
 */
export function externalUrlToAppPath(url: string): AppPath | null {
  try {
    const parsed = new URL(url);

    let path: AppPath | null = null;
    if (parsed.protocol === `${MOBILE_SCHEME}:`) {
      // flind://task/abc → /task/abc
      const host = parsed.hostname;
      if (!host) return null;
      const rest = parsed.pathname || "";
      const search = parsed.search || "";
      path = `/${host}${rest}${search}`;
    } else if (
      parsed.protocol === "https:" &&
      getUniversalLinkOrigin() !== null &&
      parsed.origin === getUniversalLinkOrigin()
    ) {
      // https://configured Flind universal-link host/task/abc → /task/abc
      const pathname = parsed.pathname || "/";
      path = `${pathname}${parsed.search || ""}`;
    }

    if (path === null) return null;
    return stripInboxSlugSuffix(path);
  } catch {
    return null;
  }
}

/**
 * Collapse `/inbox/<id>/<slug>[?query]` to `/inbox/<id>[?query]`. No-op for
 * any path that isn't an inbox-report deep link with a trailing segment.
 */
function stripInboxSlugSuffix(path: AppPath): AppPath {
  const queryStart = path.indexOf("?");
  const pathOnly = queryStart === -1 ? path : path.slice(0, queryStart);
  const query = queryStart === -1 ? "" : path.slice(queryStart);
  const segments = pathOnly.split("/").filter(Boolean);
  if (segments.length >= 3 && segments[0] === "inbox") {
    return `/inbox/${segments[1]}${query}`;
  }
  return path;
}
