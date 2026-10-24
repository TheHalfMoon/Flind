import {
  InboxMetaRow,
  InboxMetaSeparator,
  InboxMetaText,
} from "@flind/ui/features/inbox/components/InboxMetaRow";
import { InboxMetaSourceStack } from "@flind/ui/features/inbox/components/InboxMetaSourceStack";
import { getSourceProductMeta } from "@flind/ui/features/inbox/components/utils/source-product-icons";

interface InboxCardSourceMetaProps {
  repoSlug?: string | null;
  sourceProducts?: string[] | null;
  className?: string;
}

export function InboxCardSourceMeta({
  repoSlug,
  sourceProducts,
  className,
}: InboxCardSourceMetaProps) {
  const hasKnownSource = (sourceProducts ?? []).some(
    (key) => getSourceProductMeta(key) !== null,
  );
  if (!repoSlug && !hasKnownSource) {
    return null;
  }

  return (
    <InboxMetaRow className={className ?? "mt-1.5"}>
      {repoSlug ? <InboxMetaText>{repoSlug}</InboxMetaText> : null}
      {repoSlug && hasKnownSource ? <InboxMetaSeparator /> : null}
      {hasKnownSource ? (
        <InboxMetaSourceStack sourceProducts={sourceProducts} />
      ) : null}
    </InboxMetaRow>
  );
}
