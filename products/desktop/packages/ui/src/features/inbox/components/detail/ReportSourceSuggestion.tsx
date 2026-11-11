import { ArrowSquareOutIcon } from "@phosphor-icons/react";
import { reportAgeHours } from "@flind/core/inbox/engagement";
import { sourceSuggestionTarget } from "@flind/core/inbox/sourceSuggestion";
import { Button } from "@flind/quill";
import { ANALYTICS_EVENTS } from "@flind/shared";
import type {
  SignalReport,
  SignalReportSourceSuggestion,
} from "@flind/shared/types";
import { getSourceProductMeta } from "@flind/ui/features/inbox/components/utils/source-product-icons";
import { track } from "@flind/ui/shell/analytics";
import { openExternalUrl } from "@flind/ui/shell/openExternal";
import { projectPathUrl } from "@flind/ui/utils/posthogLinks";
import { useEffect, useEffectEvent } from "react";

function suggestionEventProperties(report: SignalReport, product: string) {
  return {
    report_id: report.id,
    report_age_hours: reportAgeHours(report.created_at),
    priority: report.priority ?? null,
    actionability: report.actionability ?? null,
    has_pr: !!report.implementation_pr_url,
    product,
  };
}

/**
 * A product the team doesn't use that would have given this report better
 * evidence, shown after the evidence with a link to the product in Flind.
 */
export function ReportSourceSuggestion({
  report,
  suggestion,
}: {
  report: SignalReport;
  suggestion: SignalReportSourceSuggestion;
}) {
  const target = sourceSuggestionTarget(suggestion.product);
  const url = target ? projectPathUrl(target.path) : null;
  const shown = url !== null;

  const trackShown = useEffectEvent(() => {
    track(
      ANALYTICS_EVENTS.INBOX_REPORT_SOURCE_SUGGESTION_SHOWN,
      suggestionEventProperties(report, suggestion.product),
    );
  });

  // biome-ignore lint/correctness/useExhaustiveDependencies: once per report and product, not on every report refetch.
  useEffect(() => {
    if (shown) {
      trackShown();
    }
  }, [shown, report.id, suggestion.product]);

  if (!target || !url) return null;

  return (
    <ReportSourceSuggestionView
      product={suggestion.product}
      reason={suggestion.reason}
      actionLabel={target.actionLabel}
      url={url}
      onOpen={() => {
        track(
          ANALYTICS_EVENTS.INBOX_REPORT_SOURCE_SUGGESTION_CLICKED,
          suggestionEventProperties(report, suggestion.product),
        );
        openExternalUrl(url);
      }}
    />
  );
}

export function ReportSourceSuggestionView({
  product,
  reason,
  actionLabel,
  url,
  onOpen,
}: {
  product: string;
  reason: string;
  actionLabel: string;
  url: string;
  onOpen: () => void;
}) {
  const meta = getSourceProductMeta(product);

  return (
    <div className="flex flex-col gap-2 rounded-md border border-border border-dashed p-3">
      <div className="flex items-center gap-1.5 text-muted-foreground text-xs">
        {meta && (
          <meta.Icon
            size={13}
            className="shrink-0"
            style={{ color: meta.color }}
          />
        )}
        <span className="font-medium">{meta?.label ?? product}</span>
        <span>· Not set up in this project</span>
      </div>
      <p className="m-0 text-foreground text-xs">{reason}</p>
      <Button
        // biome-ignore lint/a11y/useAnchorContent: Button renders its children inside the anchor.
        render={<a href={url} target="_blank" rel="noreferrer" />}
        nativeButton={false}
        variant="outline"
        size="sm"
        className="self-start"
        onClick={(event) => {
          // The host opens external URLs, so the anchor's own navigation must not run too.
          event.preventDefault();
          onOpen();
        }}
      >
        <ArrowSquareOutIcon size={12} />
        {actionLabel}
      </Button>
    </div>
  );
}
