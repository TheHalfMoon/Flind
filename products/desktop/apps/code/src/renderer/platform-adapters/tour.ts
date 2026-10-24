import { registerTour } from "@flind/core/tour/tourRegistry";
import { useOnboardingStore } from "@flind/ui/features/onboarding/onboardingStore";
import { useTourStore } from "@flind/ui/features/tour/tourStore";
import { createFirstTaskTour } from "@flind/ui/features/tour/tours/createFirstTaskTour";

export function initTours(): void {
  registerTour(createFirstTaskTour);
  const { hasCompletedOnboarding } = useOnboardingStore.getState();
  useTourStore.getState().applyReturningUserMigration(hasCompletedOnboarding);
}
