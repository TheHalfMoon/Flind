export type PostHogRefKind = "app" | "code" | "docs" | "website";

export interface ParsedPostHogUrl {
  kind: PostHogRefKind;
  defaultLabel: string;
  normalizedUrl: string;
  refId: string | null;
}

export interface ParsePostHogUrlOptions {
  appBaseUrl?: string | null;
  codeBaseUrl?: string | null;
}

const FLIND_CODE_PATH_PATTERN = /^\/(?:task|inbox)(?:\/|$)/;

function decodeSegment(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment;
  }
}

function humanizeSegment(segment: string): string {
  const text = decodeSegment(segment).replace(/[-_]+/g, " ").trim();
  if (!text) return "";
  return `${text.charAt(0).toUpperCase()}${text.slice(1)}`;
}

function labelWithId(title: string, refId: string | null): string {
  return refId ? `${title} (${decodeSegment(refId)})` : title;
}

function joinLabel(prefix: string, parts: string[]): string {
  const compactParts = parts.filter(Boolean);
  return compactParts.length > 0
    ? `${prefix} / ${compactParts.join(" / ")}`
    : prefix;
}

function fallbackLabel(prefix: string, segments: string[]): string {
  return joinLabel(prefix, segments.slice(0, 2).map(humanizeSegment));
}

function labelForCode(segments: string[]): string {
  if (segments[0] === "task") {
    return segments[2] === "run"
      ? labelWithId("Code / Task run", segments[3] ?? null)
      : labelWithId("Code / Task", segments[1] ?? null);
  }

  if (segments[0] === "inbox") {
    return labelWithId("Code / Inbox", segments[1] ?? null);
  }

  return fallbackLabel("Code", segments);
}

function refIdForCode(segments: string[]): string | null {
  if (segments[0] === "task") {
    return segments[2] === "run"
      ? (segments[3] ?? null)
      : (segments[1] ?? null);
  }

  if (segments[0] === "inbox") {
    return segments[1] ?? null;
  }

  return null;
}

function labelForProjectView(
  parsed: URL,
  projectSegments: string[],
): string | null {
  const [section, refId, nestedId] = projectSegments;

  switch (section) {
    case "feature-flags":
    case "feature_flags": {
      const search = parsed.searchParams.get("search")?.trim();
      if (refId) return labelWithId("Feature flag", refId);
      if (search) return `Feature flags / ${search}`;
      return "Feature flags";
    }
    case "experiments":
      return refId ? labelWithId("Experiment", refId) : "Experiments";
    case "insights":
      return refId ? labelWithId("Insight", refId) : "Insights";
    case "dashboard":
    case "dashboards":
      return refId ? labelWithId("Dashboard", refId) : "Dashboards";
    case "data-management":
      if (refId === "events" && nestedId) {
        return labelWithId("Event", nestedId);
      }
      return "Data management";
    case "settings":
      return refId ? `Settings / ${humanizeSegment(refId)}` : "Settings";
    case "session_replay":
    case "replay":
    case "recordings":
      return refId ? labelWithId("Replay", refId) : "Replay";
    case "error_tracking":
      return refId ? labelWithId("Error", refId) : "Error tracking";
    case "sql":
      return parsed.searchParams.get("open_query")?.trim()
        ? "SQL query"
        : "SQL editor";
    default:
      return null;
  }
}

function labelForApp(parsed: URL, segments: string[]): string {
  const [section, refId] = segments;

  switch (section) {
    case "insights":
      return refId ? labelWithId("Insight", refId) : "Insights";
    case "dashboard":
    case "dashboards":
      return refId ? labelWithId("Dashboard", refId) : "Dashboards";
    case "replay":
    case "recordings":
    case "session_replay":
      return refId ? labelWithId("Replay", refId) : "Replay";
    case "feature-flags":
    case "feature_flags":
      return refId ? labelWithId("Feature flag", refId) : "Feature flags";
    case "experiments":
      return refId ? labelWithId("Experiment", refId) : "Experiments";
  }

  if (segments[0] === "project" && segments[1]) {
    const projectLabel = labelForProjectView(parsed, segments.slice(2));
    if (projectLabel) return projectLabel;
  }

  return fallbackLabel("Flind", segments);
}

function refIdForApp(_parsed: URL, segments: string[]): string | null {
  const [section, refId] = segments;

  switch (section) {
    case "insights":
    case "dashboard":
    case "dashboards":
    case "replay":
    case "recordings":
    case "session_replay":
    case "feature-flags":
    case "feature_flags":
    case "experiments":
      return refId ?? null;
    case "project":
      switch (segments[2]) {
        case "feature-flags":
        case "feature_flags":
        case "experiments":
        case "insights":
        case "dashboard":
        case "dashboards":
        case "session_replay":
        case "replay":
        case "recordings":
        case "error_tracking":
          return segments[3] ?? null;
        case "data-management":
          return segments[3] === "events" ? (segments[4] ?? null) : null;
        default:
          return null;
      }
    default:
      return null;
  }
}

function ensureTrailingSlash(url: string): string {
  return url.endsWith("/") ? url : `${url}/`;
}

function resolvePostHogUrl(
  text: string,
  options: ParsePostHogUrlOptions,
): URL | null {
  const trimmed = text.trim();

  if (trimmed.startsWith("/")) {
    const baseUrl = FLIND_CODE_PATH_PATTERN.test(trimmed)
      ? options.codeBaseUrl
      : options.appBaseUrl;

    if (!baseUrl) return null;

    try {
      return new URL(trimmed, ensureTrailingSlash(baseUrl));
    } catch {
      return null;
    }
  }

  let parsed: URL;
  try {
    parsed = new URL(trimmed);
  } catch {
    return null;
  }

  return parsed;
}

/**
 * The compact reference chip recognizes configured Flind service origins
 * only. A copied vendor URL is an ordinary external link, never trusted as
 * a first-party application/task reference.
 *
 * Preserve exported type/function names as compatibility surfaces while
 * migrating downstream consumers separately.
 */
function approvedFlindOrigin(base: string | null | undefined): string | null {
  if (!base) return null;
  let url: URL;
  try {
    url = new URL(base);
  } catch {
    return null;
  }
  const hostname = url.hostname.toLowerCase().replace(/\.+$/, "");
  const loopback =
    hostname === "localhost" ||
    hostname.endsWith(".localhost") ||
    hostname === "127.0.0.1" ||
    hostname === "[::1]";
  if (
    !hostname ||
    hostname === "posthog.com" ||
    hostname.endsWith(".posthog.com") ||
    (url.protocol !== "https:" && !(url.protocol === "http:" && loopback)) ||
    url.username ||
    url.password ||
    url.pathname !== "/" ||
    url.search ||
    url.hash
  ) {
    return null;
  }
  return url.origin;
}

export function parsePostHogUrl(
  text: string,
  options: ParsePostHogUrlOptions = {},
): ParsedPostHogUrl | null {
  const parsed = resolvePostHogUrl(text, options);
  if (!parsed || parsed.username || parsed.password) return null;
  const appOrigin = approvedFlindOrigin(options.appBaseUrl);
  const codeOrigin = approvedFlindOrigin(options.codeBaseUrl);
  const segments = parsed.pathname.split("/").filter(Boolean);

  if (
    codeOrigin &&
    parsed.origin === codeOrigin &&
    (appOrigin !== codeOrigin || FLIND_CODE_PATH_PATTERN.test(parsed.pathname))
  ) {
    return {
      kind: "code",
      defaultLabel: labelForCode(segments),
      normalizedUrl: parsed.toString(),
      refId: refIdForCode(segments),
    };
  }

  if (appOrigin && parsed.origin === appOrigin) {
    return {
      kind: "app",
      defaultLabel: labelForApp(parsed, segments),
      normalizedUrl: parsed.toString(),
      refId: refIdForApp(parsed, segments),
    };
  }

  return null;
}
