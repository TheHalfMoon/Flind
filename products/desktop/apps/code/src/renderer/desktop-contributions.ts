import { autoresearchCoreModule } from "@flind/core/autoresearch/autoresearch.module";
import { taskThreadCoreModule } from "@flind/core/canvas/taskThread.module";
import { inboxCoreModule } from "@flind/core/inbox/inbox.module";
import { githubConnectModule } from "@flind/core/integrations/githubConnect.module";
import { localMcpCoreModule } from "@flind/core/local-mcp/local-mcp.module";
import { onboardingModule } from "@flind/core/onboarding/onboarding.module";
import { setupCoreModule } from "@flind/core/setup/setup.module";
import { skillsCoreModule } from "@flind/core/skills/skills.module";
import { speechCoreModule } from "@flind/core/speech/speech.module";
import { CONTRIBUTION } from "@flind/di/contribution";
import { agentUiModule } from "@flind/ui/features/agent/agent.module";
import { authUiModule } from "@flind/ui/features/auth/auth.module";
import { billingUiModule } from "@flind/ui/features/billing/billing.module";
import { browserTabsUiModule } from "@flind/ui/features/browser-tabs/browser-tabs.module";
import { taskActivityUiModule } from "@flind/ui/features/canvas/task-activity/taskActivity.module";
import { cloneUiModule } from "@flind/ui/features/clone/clone.module";
import { connectivityUiModule } from "@flind/ui/features/connectivity/connectivity.module";
import { discordPresenceUiModule } from "@flind/ui/features/discord-presence/discordPresence.module";
import { fileWatcherUiModule } from "@flind/ui/features/file-watcher/file-watcher.module";
import { focusUiModule } from "@flind/ui/features/focus/focus.module";
import { missionControlUiModule } from "@flind/ui/features/mission-control/missionControl.module";
import { notificationsUiModule } from "@flind/ui/features/notifications/notifications.module";
import { provisioningUiModule } from "@flind/ui/features/provisioning/provisioning.module";
import { settingsUiModule } from "@flind/ui/features/settings/settings.module";
import { setupUiModule } from "@flind/ui/features/setup/setup.module";
import { workspaceUiModule } from "@flind/ui/features/workspace/workspace.module";
import {
  AnalyticsBootContribution,
  InboxDemoDevContribution,
} from "@renderer/contributions/app-boot.contributions";
import { container } from "@renderer/di/container";

export function registerDesktopContributions(): void {
  for (const module of [
    agentUiModule,
    authUiModule,
    autoresearchCoreModule,
    billingUiModule,
    taskActivityUiModule,
    taskThreadCoreModule,
    browserTabsUiModule,
    cloneUiModule,
    connectivityUiModule,
    discordPresenceUiModule,
    fileWatcherUiModule,
    focusUiModule,
    githubConnectModule,
    inboxCoreModule,
    localMcpCoreModule,
    missionControlUiModule,
    notificationsUiModule,
    onboardingModule,
    provisioningUiModule,
    settingsUiModule,
    setupCoreModule,
    setupUiModule,
    skillsCoreModule,
    speechCoreModule,
    workspaceUiModule,
  ]) {
    container.load(module);
  }

  container.bind(CONTRIBUTION).to(AnalyticsBootContribution).inSingletonScope();
  container.bind(CONTRIBUTION).to(InboxDemoDevContribution).inSingletonScope();
}
