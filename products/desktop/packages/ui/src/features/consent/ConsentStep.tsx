import { ArrowLeft, ArrowRight } from "@phosphor-icons/react";
import { Button } from "@flind/quill";
import { useIsOrgAdmin } from "@flind/ui/features/auth/useOrgRole";
import { StepActions } from "@flind/ui/features/onboarding/components/StepActions";
import { LoadingState } from "@flind/ui/primitives/LoadingState";
import { AnimatePresence, motion } from "framer-motion";
import { ConsentErrorContent } from "./ConsentErrorContent";
import { ConsentPanel } from "./ConsentPanel";
import { useConsentAnalytics } from "./consentAnalytics";
import { useOrgConsent } from "./useOrgConsent";

interface ConsentStepProps {
  onNext: () => void;
  onBack?: () => void;
  requirements?: {
    needsAiConsent: boolean;
    needsBetaTerms: boolean;
  };
  onSubmittingChange?: (isSubmitting: boolean) => void;
}

export function ConsentStep({
  onNext,
  onBack,
  requirements,
}: ConsentStepProps) {
  const consent = useOrgConsent();
  const { isAdmin } = useIsOrgAdmin();
  useConsentAnalytics(consent, isAdmin === true, "onboarding_step");

  return (
    <div className="flex h-full items-center px-8">
      <div className="flex h-full w-full flex-col items-center pt-[24px] pb-[40px]">
        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
          <div className="m-auto w-full max-w-[480px]">
            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={consent.status}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.16 }}
              >
                {consent.status === "loading" ? (
                  <LoadingState />
                ) : consent.status === "error" ? (
                  <ConsentErrorContent onRetry={consent.retry} />
                ) : (
                  <ConsentPanel
                    consent={consent}
                    requirements={requirements}
                    isAdmin={isAdmin === true}
                  />
                )}
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
        <StepActions
          primaryAction={
            <Button
              variant="primary"
              size="lg"
              className="h-10 px-4 text-sm"
              disabled={consent.status !== "resolved" || !consent.satisfied}
              onClick={onNext}
            >
              Next
              <ArrowRight size={16} />
            </Button>
          }
        >
          {onBack && (
            <Button
              variant="outline"
              size="lg"
              className="h-10 px-4 text-sm"
              onClick={onBack}
            >
              <ArrowLeft size={16} />
              Back
            </Button>
          )}
        </StepActions>
      </div>
    </div>
  );
}
