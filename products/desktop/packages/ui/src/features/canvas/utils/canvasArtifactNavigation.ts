import { openExternalUrl } from "@flind/ui/shell/openExternal";
import { parseHttpsUrl, parseShareLink } from "@flind/ui/utils/posthogLinks";
import { navigateToShareTarget } from "@flind/ui/utils/shareLinks";
import { getPostHogUrl } from "@flind/ui/utils/urls";

export function canvasArtifactOpenHandler(
  url: string | null,
): (() => void) | undefined {
  if (!url) return undefined;
  const target = parseShareLink(url);
  if (!target) return undefined;

  const currentUrl = getPostHogUrl("/");
  try {
    if (currentUrl && new URL(url).origin === new URL(currentUrl).origin) {
      return () => navigateToShareTarget(target);
    }
  } catch {
    return undefined;
  }

  const safeExternalUrl = parseHttpsUrl(url);
  return safeExternalUrl
    ? () => openExternalUrl(safeExternalUrl.href)
    : undefined;
}
