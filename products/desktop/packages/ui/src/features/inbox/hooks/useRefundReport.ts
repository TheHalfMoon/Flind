import { inboxReportKeys } from "@flind/core/inbox/inboxQuery";
import { computeRefundEligibility } from "@flind/core/inbox/refundEligibility";
import { SIGNALS_PR_REFUNDS_FLAG } from "@flind/shared";
import type {
  SignalReport,
  SignalReportRefundReason,
} from "@flind/shared/types";
import { useAuthenticatedClient } from "@flind/ui/features/auth/authClient";
import { useFeatureFlag } from "@flind/ui/features/feature-flags/useFeatureFlag";
import { useReportActionTracker } from "@flind/ui/features/inbox/hooks/useReportActionTracker";
import { toast } from "@flind/ui/primitives/toast";
import { useMutation, useQueryClient } from "@tanstack/react-query";

/**
 * Refund-and-archive a report's PR, mirroring the web inbox. The button is
 * offered only when the flag is on and the report has a billable PR that
 * hasn't been refunded; the server enforces the same rules, so `canRefund`
 * is a display gate.
 */
export function useRefundReport(report: SignalReport) {
  const client = useAuthenticatedClient();
  const queryClient = useQueryClient();
  const flagEnabled = useFeatureFlag(SIGNALS_PR_REFUNDS_FLAG);
  const trackAction = useReportActionTracker(report);

  const { canRefund, disabledReason } = computeRefundEligibility(
    report,
    flagEnabled,
  );

  const mutation = useMutation({
    mutationFn: (input: { reason: SignalReportRefundReason; note?: string }) =>
      client.refundSignalReport(report.id, input),
    onSuccess: (_updatedReport, input) => {
      trackAction("refund", {
        refund_reason: input.reason,
        ...(input.note ? { refund_note: input.note } : {}),
      });
      toast.success("PR refunded. The report has been archived.");
      queryClient.invalidateQueries({ queryKey: inboxReportKeys.all });
    },
    onError: (error) => {
      toast.error(
        error instanceof Error ? error.message : "Couldn't refund this PR.",
      );
    },
  });

  return { canRefund, disabledReason, mutation };
}
