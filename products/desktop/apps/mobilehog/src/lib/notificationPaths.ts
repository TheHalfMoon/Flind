/**
 * A notification opens only a task or report on this Flind Studio instance.
 * Never treat arbitrary URL protocols or an inherited vendor's app scheme
 * as a route inside Flind.
 */
export function notificationUrlToAppPath(raw: unknown): string | null {
  if (typeof raw !== "string") return null;
  let path: string;
  if (raw.startsWith("/")) {
    // Avoid URLs with an authority (//evil.example) or backslash confusion.
    if (raw.startsWith("//") || raw.includes("\\")) return null;
    path = raw;
  } else {
    let uri: URL;
    try {
      uri = new URL(raw);
    } catch {
      return null;
    }
    if (
      uri.protocol !== "flind-studio:" ||
      uri.username ||
      uri.password ||
      uri.hash ||
      !["task", "report"].includes(uri.hostname)
    ) {
      return null;
    }
    path = "/" + uri.hostname + uri.pathname + uri.search;
  }

  // Explicitly guard against cross-route navigation and arbitrary paths.
  // IDs are one path segment; querystrings are preserved for router state.
  if (!/^\/(?:task|report)\/[A-Za-z0-9_-]+(?:\?[^#]*)?$/.test(path)) return null;
  return path;
}

export function notificationTaskIdToPath(taskId: unknown): string | null {
  if (typeof taskId !== "string" || !/^[A-Za-z0-9_-]+$/.test(taskId)) return null;
  return "/task/" + taskId;
}
