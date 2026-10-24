import { GitPullRequestIcon, MagnifyingGlassIcon } from "@phosphor-icons/react";
import { parsePrUrl } from "@flind/core/inbox/reportPresentation";
import type { SignalReport } from "@flind/shared/types";
import { ReportFeedbackFooter } from "@flind/ui/features/inbox/components/detail/ReportFeedbackFooter";
import { InboxDetailFrame } from "@flind/ui/features/inbox/components/InboxDetailFrame";
import { InboxMetaSeparator } from "@flind/ui/features/inbox/components/InboxMetaRow";
import { InboxReportDetailGate } from "@flind/ui/features/inbox/components/InboxReportDetailGate";
import { PrDiffStats } from "@flind/ui/features/inbox/components/PrDiffStats";
import { ReportChatLayout } from "@flind/ui/features/inbox/components/ReportDetail";
import { ReportDetailActions } from "@flind/ui/features/inbox/components/ReportDetailActions";
import { ReportReviewersSection } from "@flind/ui/features/inbox/components/ReportReviewersSection";
import { ReportImplementationPrLink } from "@flind/ui/features/inbox/components/utils/ReportImplementationPrLink";
import { ReportTrackerIssueLink } from "@flind/ui/features/inbox/components/utils/ReportTrackerIssueLink";
import { PrCommentsSection } from "@flind/ui/features/pr-review/PrCommentsSection";
import { PrDecisionBlock } from "@flind/ui/features/pr-review/PrDecisionBlock";
import { PrFilesChangedSection } from "@flind/ui/features/pr-review/PrFilesChangedSection";

interface PullRequestDetailProps {
  reportId: string;
  cachedReport?: SignalReport | null;
}

export function PullRequestDetail({
  reportId,
  cachedReport = null,
}: PullRequestDetailProps) {
  return (
    <InboxReportDetailGate
      reportId={reportId}
      cachedReport={cachedReport}
      backTo="/inbox/pulls"
      backLabel="Back to pull requests"
      missingCopy="This pull request couldn't be found. It may have been deleted."
    >
      {(report) => <PullRequestDetailContent report={report} />}
    </InboxReportDetailGate>
  );
}

/**
 * A report whose PR exists reads as: the story (summary + charts), then the
 * decision (approve / merge, big), then the discussion. The per-check CI
 * matrix, the runs log, and the activity log deliberately don't render —
 * they're pipeline machinery, and the decision block distills what matters
 * from them into one line.
 */
export function PullRequestDetailContent({ report }: { report: SignalReport }) {
  const prRef = report.implementation_pr_url
    ? parsePrUrl(report.implementation_pr_url)
    : null;
  const prUrl = prRef ? report.implementation_pr_url : null;

  return (
    <ReportChatLayout report={report}>
      <InboxDetailFrame
        report={report}
        fallbackTitle="Untitled pull request"
        metaSuffix={
          prUrl ? (
            <>
              <InboxMetaSeparator />
              <ReportImplementationPrLink prUrl={prUrl} size="md" />
              <ReportTrackerIssueLink report={report} />
            </>
          ) : (
            <ReportTrackerIssueLink report={report} />
          )
        }
        primaryAction={
          <ReportDetailActions
            report={report}
            prUrl={prUrl}
            placement="header"
          />
        }
        showDismiss={false}
        summarySection={{ Icon: GitPullRequestIcon, title: "Summary" }}
        secondaryTab={
          prUrl
            ? {
                label: (
                  <>
                    Changed code
                    <PrDiffStats prUrl={prUrl} hideWhileLoading />
                  </>
                ),
                content: <PrFilesChangedSection prUrl={prUrl} bare />,
              }
            : undefined
        }
        belowSummary={
          prUrl && (
            <>
              <PrDecisionBlock prUrl={prUrl} />
              <PrCommentsSection prUrl={prUrl} />
            </>
          )
        }
        footer={<ReportFeedbackFooter report={report} />}
        evidenceSection={{ Icon: MagnifyingGlassIcon, title: "Evidence" }}
      >
        <ReportReviewersSection report={report} />
      </InboxDetailFrame>
    </ReportChatLayout>
  );
}
