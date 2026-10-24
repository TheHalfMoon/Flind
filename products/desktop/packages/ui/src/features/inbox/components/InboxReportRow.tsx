import type { ReportImplementationState } from "@flind/core/inbox/reportImplementation";
import type { SignalReport } from "@flind/shared/types";
import { InboxReportContextMenu } from "@flind/ui/features/inbox/components/InboxReportContextMenu";
import { InboxReportRowView } from "@flind/ui/features/inbox/components/InboxReportRowView";
import { ReportRestoreButton } from "@flind/ui/features/inbox/components/ReportRestoreButton";
import { SuggestedReviewerAvatarStack } from "@flind/ui/features/inbox/components/SuggestedReviewerAvatarStack";
import { useInboxReportDetailPrefetch } from "@flind/ui/features/inbox/hooks/useInboxReportDetailPrefetch";
import { navigateToInboxReportDetail } from "@flind/ui/router/navigationBridge";
import { openExternalUrl } from "@flind/ui/shell/openExternal";

export function InboxReportRow({
  report,
  implementationState,
}: {
  report: SignalReport;
  implementationState?: ReportImplementationState | null;
}): React.JSX.Element {
  const { pointerHandlers } = useInboxReportDetailPrefetch({
    to: "/reports/$reportId",
    params: { reportId: report.id },
  });

  return (
    <InboxReportContextMenu report={report}>
      <InboxReportRowView
        report={report}
        implementationState={implementationState}
        prefetchHandlers={pointerHandlers}
        reviewers={<SuggestedReviewerAvatarStack report={report} />}
        restoreAction={<ReportRestoreButton report={report} />}
        onOpen={() => navigateToInboxReportDetail(report.id)}
        onOpenPr={openExternalUrl}
      />
    </InboxReportContextMenu>
  );
}
