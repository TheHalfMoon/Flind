import type { CloudRegion } from "@flind/shared";
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
import { openTaskInput } from "@flind/ui/router/useOpenTask";
import { inject, injectable } from "inversify";

// Web counterpart of the desktop RendererAuthSideEffects. Identical store/query
// coordination, minus the desktop SessionService reset — web cloud sessions are
// owned by the core SessionService, not a renderer singleton.
@injectable()
export class WebAuthSideEffects implements IAuthSideEffects {
  constructor(
    @inject(BROWSER_TABS_CLIENT)
    private readonly browserTabsClient: BrowserTabsClient,
  ) {}

  onAuthSuccess(_region: CloudRegion, _projectId: number | null): void {
    resetInboxReportActionDrafts();
    void refreshAuthStateQuery();
    useAuthUiStateStore.getState().clearStaleRegion();
  }

  beforeProjectSwitch(): void {}

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
