import type { CloudRegion } from "@flind/shared";
import { ANALYTICS_EVENTS } from "@flind/shared/analytics-events";
import {
  clearAuthScopedQueries,
  refreshAuthStateQuery,
} from "@flind/ui/features/auth/authQueries";
import { useAuthUiStateStore } from "@flind/ui/features/auth/authUiStateStore";
import type { IAuthSideEffects } from "@flind/ui/features/auth/identifiers";
import {
  BROWSER_TABS_CLIENT,
  type BrowserTabsClient,
} from "@flind/ui/features/browser-tabs/browserTabsClient";
import { resetCurrentChannel } from "@flind/ui/features/canvas/stores/currentChannelStore";
import { resetInboxReportActionDrafts } from "@flind/ui/features/inbox/stores/inboxReportActionDraftStore";
import { useOnboardingStore } from "@flind/ui/features/onboarding/onboardingStore";
import { resetSessionService } from "@flind/ui/features/sessions/sessionServiceHost";
import { openTaskInput } from "@flind/ui/router/useOpenTask";
import { track } from "@flind/ui/shell/analytics";
import { inject, injectable } from "inversify";

@injectable()
export class RendererAuthSideEffects implements IAuthSideEffects {
  constructor(
    @inject(BROWSER_TABS_CLIENT)
    private readonly browserTabsClient: BrowserTabsClient,
  ) {}

  onAuthSuccess(region: CloudRegion, projectId: number | null): void {
    resetInboxReportActionDrafts();
    void refreshAuthStateQuery();
    useAuthUiStateStore.getState().clearStaleRegion();
    track(ANALYTICS_EVENTS.USER_LOGGED_IN, {
      project_id: projectId?.toString() ?? "",
      region,
    });
  }

  beforeProjectSwitch(): void {
    resetSessionService();
  }

  async onProjectSelected(): Promise<void> {
    clearAuthScopedQueries();
    resetInboxReportActionDrafts();
    // Before openTaskInput, which files a new task into the scoped channel —
    // a channel id from the project we just left.
    resetCurrentChannel();
    await Promise.all([
      refreshAuthStateQuery(),
      this.browserTabsClient.reset(),
    ]);
    openTaskInput();
  }

  async onLogout(previousRegion: CloudRegion | null): Promise<void> {
    track(ANALYTICS_EVENTS.USER_LOGGED_OUT);
    resetSessionService();
    clearAuthScopedQueries();
    resetInboxReportActionDrafts();
    if (previousRegion) {
      useAuthUiStateStore.getState().setStaleRegion(previousRegion);
    }
    resetCurrentChannel();
    await this.browserTabsClient.reset();
    openTaskInput();
    useOnboardingStore.getState().resetSelections();
  }
}
