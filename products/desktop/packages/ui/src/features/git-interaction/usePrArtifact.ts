import type { Icon } from "@phosphor-icons/react";
import {
  getPrVisualConfig,
  parsePrNumber,
} from "@flind/core/git-interaction/prStatus";
import { getPrVisualIcon } from "@flind/ui/features/git-interaction/prIcon";
import { usePrDetails } from "@flind/ui/features/git-interaction/usePrDetails";
import { parseHttpsUrl } from "@flind/ui/utils/posthogLinks";

export function usePrArtifact(url: string | null): {
  safeUrl: string | null;
  prNumber: string | undefined;
  title: string;
  stateLabel: string | null;
  Icon: Icon;
  iconColor: string;
  accentColor: string;
} {
  const parsed = url ? parseHttpsUrl(url) : null;
  const safeUrl = parsed?.origin === "https://github.com" ? parsed.href : null;
  const {
    meta: { state, merged, draft },
  } = usePrDetails(safeUrl);

  const config = getPrVisualConfig(state ?? "open", merged, draft);
  const prNumber = safeUrl ? parsePrNumber(safeUrl) : undefined;

  return {
    safeUrl,
    prNumber,
    title: prNumber ? `Pull request #${prNumber}` : "Pull request",
    // Only once the state has resolved, to avoid a flash of "Open".
    stateLabel: state ? config.label : null,
    Icon: getPrVisualIcon(config.icon),
    iconColor: `var(--${config.color}-9)`,
    accentColor: config.color,
  };
}
