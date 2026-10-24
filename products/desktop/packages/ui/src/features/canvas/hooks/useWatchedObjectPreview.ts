import type { EvidencePreview } from "@flind/api-client/evidence-previews";
import type { ContextObject } from "@flind/core/canvas/contextDocument";
import { parsePostHogObjectUrl } from "@flind/core/canvas/contextDocument";
import {
  EVIDENCE_PREVIEW_STALE_TIME,
  evidencePreviewQueryKey,
} from "@flind/ui/features/editor/evidencePreview";
import { useAuthenticatedQuery } from "@flind/ui/hooks/useAuthenticatedQuery";
import { usePostHogHost } from "./usePostHogHost";

export function useWatchedObjectPreview(object: ContextObject) {
  const host = usePostHogHost();
  const parsed = parsePostHogObjectUrl(object.url, host);
  const target = parsed ? { kind: parsed.kind, id: parsed.id } : null;
  return useAuthenticatedQuery<EvidencePreview | null>(
    target
      ? evidencePreviewQueryKey(target)
      : (["evidence-preview", "none", object.url] as const),
    (client) =>
      target
        ? client.getEvidencePreview(target.kind, target.id)
        : Promise.resolve(null),
    {
      enabled: target !== null && target.kind !== "link",
      staleTime: EVIDENCE_PREVIEW_STALE_TIME,
      retry: false,
    },
  );
}
