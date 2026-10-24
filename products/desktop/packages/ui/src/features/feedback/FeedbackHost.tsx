import { useService } from "@flind/di/react";
import {
  FEEDBACK_CONTEXT_SERVICE,
  type IFeedbackContext,
} from "@flind/platform/feedback-context";
import { FeedbackModal } from "@flind/ui/features/feedback/FeedbackModal";
import { useFeedbackStore } from "@flind/ui/features/feedback/feedbackStore";

export function FeedbackHost() {
  const mode = useFeedbackStore((state) => state.mode);
  const finishFeedback = useFeedbackStore((state) => state.finish);
  const contextClient = useService<IFeedbackContext>(FEEDBACK_CONTEXT_SERVICE);

  return (
    <FeedbackModal
      mode={mode}
      onFinished={finishFeedback}
      contextClient={contextClient}
    />
  );
}
