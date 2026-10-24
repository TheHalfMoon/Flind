import { SETTINGS_BACKUP_FILES } from "@flind/platform/settings-backup-files";
import { ElectronSettingsBackupFiles } from "../platform-adapters/electron-settings-backup-files";
import { desktopGatewayTokenHost } from "../utils/gateway-override";
import "reflect-metadata";

import { readFile as fsReadFile, stat as fsStat } from "node:fs/promises";
import { join } from "node:path";
import { TypedContainer } from "@inversifyjs/strongly-typed";
import { DEFAULT_GATEWAY_MODEL } from "@flind/agent/gateway-models";
import {
  getGatewayUsageUrl,
  getLlmGatewayUrl,
} from "@flind/agent/posthog-api";
import { AuthService } from "@flind/core/auth/auth";
import { AUTH_SERVICE } from "@flind/core/auth/auth.module";
import {
  AUTH_CONNECTIVITY,
  AUTH_FETCH,
  AUTH_FETCH_EXTRA_ORIGINS,
  AUTH_OAUTH_FLOW_SERVICE,
  AUTH_PREFERENCE_STORE,
  AUTH_SESSION_STORE,
  AUTH_TOKEN_CIPHER,
  AUTH_TOKEN_OVERRIDE,
} from "@flind/core/auth/identifiers";
import { canvasCoreModule } from "@flind/core/canvas/canvas.module";
import { cloudTaskModule } from "@flind/core/cloud-task/cloud-task.module";
import {
  CLAUDE_SUBSCRIPTION_TOKEN_STORE,
  CLOUD_TASK_AUTH,
  CLOUD_TASK_SERVICE,
  MCP_RELAY_EXECUTOR,
} from "@flind/core/cloud-task/identifiers";
import { contextMenuCoreModule } from "@flind/core/context-menu/context-menu.module";
import {
  CONTEXT_MENU_CONTROLLER,
  CONTEXT_MENU_EXTERNAL_APPS_SERVICE,
} from "@flind/core/context-menu/identifiers";
import { CUSTOM_CLOUD_STORE } from "@flind/core/custom-cloud/identifiers";
import { feedbackCoreModule } from "@flind/core/feedback/feedback.module";
import { FocusHostService } from "@flind/core/focus/focus-service";
import { FocusServiceEvent } from "@flind/core/focus/identifiers";
import { gitHostModule } from "@flind/core/git/git-host.module";
import type {
  GitWorkspaceLookup,
  HostGitWorkspaceClient,
} from "@flind/core/git/host-git";
import {
  GIT_AGENT_SERVICE,
  GIT_WORKSPACE_CLIENT,
  GIT_WORKSPACE_LOOKUP,
} from "@flind/core/git/identifiers";
import { gitPrModule } from "@flind/core/git-pr/git-pr.module";
import { GIT_DIFF_SOURCE } from "@flind/core/git-pr/identifiers";
import { integrationsModule } from "@flind/core/integrations/integrations.module";
import { CanvasLinkService } from "@flind/core/links/canvas-link";
import { ChannelLinkService } from "@flind/core/links/channel-link";
import {
  CANVAS_LINK_SERVICE,
  CHANNEL_LINK_SERVICE,
  INBOX_LINK_SERVICE,
  LOOP_LINK_SERVICE,
  NEW_TASK_LINK_SERVICE,
  OPEN_TARGET_LINK_SERVICE,
  SCOUT_LINK_SERVICE,
  TASK_LINK_SERVICE,
} from "@flind/core/links/identifiers";
import { InboxLinkService } from "@flind/core/links/inbox-link";
import { LoopLinkService } from "@flind/core/links/loop-link";
import { NewTaskLinkService } from "@flind/core/links/new-task-link";
import { OpenTargetLinkService } from "@flind/core/links/open-target-link";
import { ScoutLinkService } from "@flind/core/links/scout-link";
import { TaskLinkService } from "@flind/core/links/task-link";
import type { GatewayTokenService } from "@flind/core/llm-gateway/gateway-token";
import {
  GATEWAY_TOKEN_HOST,
  GATEWAY_TOKEN_SERVICE,
  LLM_GATEWAY_HOST,
  LLM_GATEWAY_SERVICE,
} from "@flind/core/llm-gateway/identifiers";
import {
  desktopUsageUrl,
  type LlmGatewayService,
} from "@flind/core/llm-gateway/llm-gateway";
import { llmGatewayModule } from "@flind/core/llm-gateway/llm-gateway.module";
import { MCP_APPS_SERVICE } from "@flind/core/mcp-apps/identifiers";
import { mcpAppsModule } from "@flind/core/mcp-apps/mcp-apps.module";
import { NOTIFICATION_SERVICE } from "@flind/core/notification/identifiers";
import { NotificationService } from "@flind/core/notification/notification";
import {
  OAUTH_HOST,
  type OAuthCallbackReceiver,
} from "@flind/core/oauth/identifiers";
import { oauthModule } from "@flind/core/oauth/oauth.module";
import { PROVISIONING_SERVICE } from "@flind/core/provisioning/identifiers";
import { ProvisioningService } from "@flind/core/provisioning/provisioning";
import { SLEEP_SERVICE } from "@flind/core/sleep/identifiers";
import { SleepService } from "@flind/core/sleep/sleep";
import { UI_AUTH } from "@flind/core/ui/identifiers";
import { uiModule } from "@flind/core/ui/ui.module";
import {
  UPDATE_LIFECYCLE_SERVICE,
  UPDATES_SERVICE,
} from "@flind/core/updates/identifiers";
import { updatesCoreModule } from "@flind/core/updates/updates.module";
import { USAGE_HOST } from "@flind/core/usage/identifiers";
import { usageMonitorModule } from "@flind/core/usage/usage-monitor.module";
import { ROOT_LOGGER, type RootLogger } from "@flind/di/logger";
import { listFilesContainingText } from "@flind/git/queries";
import { CONNECTIVITY_CLIENT } from "@flind/host-router/ports/connectivity-client";
import {
  GIT_PR_STATUS_PROVIDER,
  type IGitPrStatus,
} from "@flind/host-router/ports/git-pr-status";
import { ANALYTICS_SERVICE } from "@flind/platform/analytics";
import { APP_LIFECYCLE_SERVICE } from "@flind/platform/app-lifecycle";
import { APP_META_SERVICE } from "@flind/platform/app-meta";
import { APP_METRICS_SERVICE } from "@flind/platform/app-metrics";
import { BUNDLED_RESOURCES_SERVICE } from "@flind/platform/bundled-resources";
import { CLIPBOARD_SERVICE } from "@flind/platform/clipboard";
import { CONTEXT_MENU_SERVICE } from "@flind/platform/context-menu";
import { CRYPTO_SERVICE } from "@flind/platform/crypto";
import { DEEP_LINK_SERVICE } from "@flind/platform/deep-link";
import { DEV_HOST_ACTIONS_SERVICE } from "@flind/platform/dev-host-actions";
import { DIALOG_SERVICE } from "@flind/platform/dialog";
import { DISK_CACHE_SERVICE } from "@flind/platform/disk-cache";
import { FEEDBACK_CONTEXT_SERVICE } from "@flind/platform/feedback-context";
import { FILE_ICON_SERVICE } from "@flind/platform/file-icon";
import { IMAGE_PROCESSOR_SERVICE } from "@flind/platform/image-processor";
import { MAIN_WINDOW_SERVICE } from "@flind/platform/main-window";
import { NOTIFIER_SERVICE } from "@flind/platform/notifier";
import { POWER_MANAGER_SERVICE } from "@flind/platform/power-manager";
import { SCREEN_CAPTURE_SERVICE } from "@flind/platform/screen-capture";
import { SECURE_STORAGE_SERVICE } from "@flind/platform/secure-storage";
import { STORAGE_PATHS_SERVICE } from "@flind/platform/storage-paths";
import { UPDATER_SERVICE } from "@flind/platform/updater";
import { URL_LAUNCHER_SERVICE } from "@flind/platform/url-launcher";
import { WORKSPACE_SETTINGS_SERVICE } from "@flind/platform/workspace-settings";
import type { WorkspaceClient } from "@flind/workspace-client/client";
import { databaseModule } from "@flind/workspace-server/db/db.module";
import {
  ARCHIVE_REPOSITORY,
  AUTH_PREFERENCE_REPOSITORY,
  AUTH_SESSION_REPOSITORY,
  DATABASE_SERVICE,
  DEFAULT_ADDITIONAL_DIRECTORY_REPOSITORY,
  REPOSITORY_REPOSITORY,
  SUSPENSION_REPOSITORY,
  WORKSPACE_REPOSITORY,
  WORKTREE_REPOSITORY,
} from "@flind/workspace-server/db/identifiers";
import { repositoriesModule } from "@flind/workspace-server/db/repositories.module";
import {
  CONNECTIVITY_SERVICE as WS_CONNECTIVITY_SERVICE,
  GIT_SERVICE as WS_GIT_SERVICE,
} from "@flind/workspace-server/di/tokens";
import { additionalDirectoriesModule } from "@flind/workspace-server/services/additional-directories/additional-directories.module";
import type { AgentService } from "@flind/workspace-server/services/agent/agent";
import { agentModule } from "@flind/workspace-server/services/agent/agent.module";
import {
  AGENT_AUTH,
  AGENT_LOGGER,
  AGENT_MCP_APPS,
  AGENT_REPO_FILES,
  AGENT_SERVICE,
  AGENT_SLEEP_COORDINATOR,
} from "@flind/workspace-server/services/agent/identifiers";
import { AgentServiceEvent } from "@flind/workspace-server/services/agent/schemas";
import { archiveModule } from "@flind/workspace-server/services/archive/archive.module";
import {
  ARCHIVE_FILE_WATCHER,
  ARCHIVE_SESSION_CANCELLER,
} from "@flind/workspace-server/services/archive/identifiers";
import { authProxyModule } from "@flind/workspace-server/services/auth-proxy/auth-proxy.module";
import {
  AUTH_PROXY_AUTH,
  GATEWAY_CREDENTIAL_SOURCE,
} from "@flind/workspace-server/services/auth-proxy/identifiers";
import { browserTabsModule } from "@flind/workspace-server/services/browser-tabs/browser-tabs.module";
import { claudeCliSessionsModule } from "@flind/workspace-server/services/claude-cli-sessions/claude-cli-sessions.module";
import { ConnectivityService } from "@flind/workspace-server/services/connectivity/service";
import { enrichmentModule } from "@flind/workspace-server/services/enrichment/enrichment.module";
import {
  ENRICHMENT_AUTH,
  ENRICHMENT_FILE_READER,
} from "@flind/workspace-server/services/enrichment/identifiers";
import { externalAppsModule } from "@flind/workspace-server/services/external-apps/external-apps.module";
import {
  EXTERNAL_APPS_SERVICE,
  EXTERNAL_APPS_STORE,
} from "@flind/workspace-server/services/external-apps/identifiers";
import type { ExternalAppsPreferences } from "@flind/workspace-server/services/external-apps/types";
import { foldersModule } from "@flind/workspace-server/services/folders/folders.module";
import { GitService } from "@flind/workspace-server/services/git/service";
import { TaskPrStatusService } from "@flind/workspace-server/services/git/task-pr-status";
import { LOGS_SERVICE } from "@flind/workspace-server/services/local-logs/identifiers";
import { localMcpModule } from "@flind/workspace-server/services/local-mcp/local-mcp.module";
import { mcpCallbackModule } from "@flind/workspace-server/services/mcp-callback/mcp-callback.module";
import { MCP_PROXY_AUTH } from "@flind/workspace-server/services/mcp-proxy/identifiers";
import { mcpProxyModule } from "@flind/workspace-server/services/mcp-proxy/mcp-proxy.module";
import { MCP_RELAY_SERVICE } from "@flind/workspace-server/services/mcp-relay/identifiers";
import { mcpRelayModule } from "@flind/workspace-server/services/mcp-relay/mcp-relay.module";
import { OAUTH_CALLBACK_SERVER } from "@flind/workspace-server/services/oauth-callback/identifiers";
import { oauthCallbackModule } from "@flind/workspace-server/services/oauth-callback/oauth-callback.module";
import { osModule } from "@flind/workspace-server/services/os/os.module";
import {
  PI_RPC_CLIENT_FACTORY,
  PI_RUNTIME_FACTORY,
  PI_SESSION_SERVICE,
} from "@flind/workspace-server/services/pi-session/identifiers";
import type { PiSessionService } from "@flind/workspace-server/services/pi-session/pi-session";
import { piSessionModule } from "@flind/workspace-server/services/pi-session/pi-session.module";
import { POSTHOG_PLUGIN_SERVICE } from "@flind/workspace-server/services/posthog-plugin/identifiers";
import { posthogPluginModule } from "@flind/workspace-server/services/posthog-plugin/posthog-plugin.module";
import { PROCESS_TRACKING_SERVICE } from "@flind/workspace-server/services/process-tracking/identifiers";
import { processTrackingModule } from "@flind/workspace-server/services/process-tracking/process-tracking.module";
import { releaseFeedModule } from "@flind/workspace-server/services/release-feed/release-feed.module";
import { SECURE_STORE_SERVICE } from "@flind/workspace-server/services/secure-store/identifiers";
import { shellModule } from "@flind/workspace-server/services/shell/shell.module";
import { skillsModule } from "@flind/workspace-server/services/skills/skills.module";
import { skillsMarketplaceModule } from "@flind/workspace-server/services/skills-marketplace/skills-marketplace.module";
import { SPEECH_SYNTHESIZER_SERVICE } from "@flind/workspace-server/services/speech/identifiers";
import {
  SUSPENSION_FILE_WATCHER,
  SUSPENSION_SERVICE,
  SUSPENSION_SESSION_CANCELLER,
} from "@flind/workspace-server/services/suspension/identifiers";
import { suspensionModule } from "@flind/workspace-server/services/suspension/suspension.module";
import { FileWatcherEventKind } from "@flind/workspace-server/services/watcher/schemas";
import { WATCHER_REGISTRY_SERVICE } from "@flind/workspace-server/services/watcher-registry/identifiers";
import { watcherRegistryModule } from "@flind/workspace-server/services/watcher-registry/watcher-registry.module";
import {
  WORKSPACE_AGENT,
  WORKSPACE_FILE_WATCHER,
  WORKSPACE_FOCUS,
  WORKSPACE_PROVISIONING,
  WORKSPACE_SERVICE,
} from "@flind/workspace-server/services/workspace/identifiers";
import type {
  WorkspaceAgent,
  WorkspaceFileWatcher,
  WorkspaceFocus,
  WorkspaceProvisioning,
} from "@flind/workspace-server/services/workspace/ports";
import type { WorkspaceService } from "@flind/workspace-server/services/workspace/workspace";
import { workspaceModule } from "@flind/workspace-server/services/workspace/workspace.module";
import { workspaceMetadataModule } from "@flind/workspace-server/services/workspace-metadata/workspace-metadata.module";
import ExternalAppsStoreImpl from "electron-store";
import type { FileWatcherBridge } from "../index";
import { DesktopPiRpcClientFactory } from "../platform-adapters/desktop-pi-rpc-client-factory";
import { DesktopPiRuntimeFactory } from "../platform-adapters/desktop-pi-runtime-factory";
import { ElectronAppLifecycle } from "../platform-adapters/electron-app-lifecycle";
import { ElectronAppMeta } from "../platform-adapters/electron-app-meta";
import { ElectronAppMetrics } from "../platform-adapters/electron-app-metrics";
import { ElectronBundledResources } from "../platform-adapters/electron-bundled-resources";
import { ElectronClaudeSubscriptionTokenStore } from "../platform-adapters/electron-claude-subscription-token-store";
import { ElectronClipboard } from "../platform-adapters/electron-clipboard";
import { ElectronContextMenu } from "../platform-adapters/electron-context-menu";
import { ElectronCrypto } from "../platform-adapters/electron-crypto";
import { ElectronCustomCloudStore } from "../platform-adapters/electron-custom-cloud-store";
import { ElectronDevHostActions } from "../platform-adapters/electron-dev-host-actions";
import { ElectronDialog } from "../platform-adapters/electron-dialog";
import { ElectronFeedbackContext } from "../platform-adapters/electron-feedback-context";
import { ElectronFileIcon } from "../platform-adapters/electron-file-icon";
import { ElectronImageProcessor } from "../platform-adapters/electron-image-processor";
import { ElectronMainWindow } from "../platform-adapters/electron-main-window";
import { MissionControlService } from "../platform-adapters/electron-mission-control";
import { electronNetFetch } from "../platform-adapters/electron-net-fetch";
import { ElectronNotifier } from "../platform-adapters/electron-notifier";
import { ElectronPowerManager } from "../platform-adapters/electron-power-manager";
import { ElectronScreenCapture } from "../platform-adapters/electron-screen-capture";
import { ElectronSecureStorage } from "../platform-adapters/electron-secure-storage";
import { ElectronStoragePaths } from "../platform-adapters/electron-storage-paths";
import { ElectronUpdater } from "../platform-adapters/electron-updater";
import { ElectronUrlLauncher } from "../platform-adapters/electron-url-launcher";
import { electronUsageThresholdStore } from "../platform-adapters/electron-usage-threshold-store";
import { ElectronWorkspaceSettings } from "../platform-adapters/electron-workspace-settings";
import { posthogNodeAnalytics } from "../platform-adapters/posthog-analytics";
import { AppLifecycleService } from "../services/app-lifecycle/service";
import {
  AuthPreferencePortAdapter,
  AuthSessionPortAdapter,
  OAuthFlowPortAdapter,
  TokenCipherPortAdapter,
} from "../services/auth/port-adapters";
import { DeepLinkService } from "../services/deep-link/service";
import { DevActionsService } from "../services/dev-actions/service";
import { DevFlagsService } from "../services/dev-flags/service";
import { DevLogsService } from "../services/dev-logs/service";
import { DevMetricsService } from "../services/dev-metrics/service";
import { DevNetworkService } from "../services/dev-network/service";
import { DiscordPresenceService } from "../services/discord-presence/service";
import { DiskCache } from "../services/disk-cache/service";
import { EncryptionService } from "../services/encryption/service";
import { SecureStoreService } from "../services/secure-store/service";
import { settingsStore } from "../services/settingsStore";
import { ElevenLabsSpeechService } from "../services/speech/service";
import { WorkspaceServerService } from "../services/workspace-server/service";
import { getUserDataDir, isDevBuild } from "../utils/env";
import { logger } from "../utils/logger";
import { rendererStore } from "../utils/store";
import type { MainBindings } from "./bindings";
import {
  APP_LIFECYCLE_SERVICE as MAIN_APP_LIFECYCLE_SERVICE,
  ARCHIVE_REPOSITORY as MAIN_ARCHIVE_REPOSITORY,
  AUTH_PREFERENCE_REPOSITORY as MAIN_AUTH_PREFERENCE_REPOSITORY,
  AUTH_SERVICE as MAIN_AUTH_SERVICE,
  AUTH_SESSION_REPOSITORY as MAIN_AUTH_SESSION_REPOSITORY,
  CANVAS_LINK_SERVICE as MAIN_CANVAS_LINK_SERVICE,
  CHANNEL_LINK_SERVICE as MAIN_CHANNEL_LINK_SERVICE,
  CLOUD_TASK_SERVICE as MAIN_CLOUD_TASK_SERVICE,
  CONTEXT_MENU_SERVICE as MAIN_CONTEXT_MENU_SERVICE,
  DATABASE_SERVICE as MAIN_DATABASE_SERVICE,
  DEEP_LINK_SERVICE as MAIN_DEEP_LINK_SERVICE,
  DEFAULT_ADDITIONAL_DIRECTORY_REPOSITORY as MAIN_DEFAULT_ADDITIONAL_DIRECTORY_REPOSITORY,
  DEV_ACTIONS_SERVICE as MAIN_DEV_ACTIONS_SERVICE,
  DEV_FLAGS_SERVICE as MAIN_DEV_FLAGS_SERVICE,
  DEV_LOGS_SERVICE as MAIN_DEV_LOGS_SERVICE,
  DEV_METRICS_SERVICE as MAIN_DEV_METRICS_SERVICE,
  DEV_NETWORK_SERVICE as MAIN_DEV_NETWORK_SERVICE,
  DISCORD_PRESENCE_SERVICE as MAIN_DISCORD_PRESENCE_SERVICE,
  ENCRYPTION_SERVICE as MAIN_ENCRYPTION_SERVICE,
  EXTERNAL_APPS_SERVICE as MAIN_EXTERNAL_APPS_SERVICE,
  FILE_WATCHER_SERVICE as MAIN_FILE_WATCHER_SERVICE,
  FS_SERVICE as MAIN_FS_SERVICE,
  INBOX_LINK_SERVICE as MAIN_INBOX_LINK_SERVICE,
  LLM_GATEWAY_SERVICE as MAIN_LLM_GATEWAY_SERVICE,
  LOOP_LINK_SERVICE as MAIN_LOOP_LINK_SERVICE,
  MCP_APPS_SERVICE as MAIN_MCP_APPS_SERVICE,
  MISSION_CONTROL_SERVICE as MAIN_MISSION_CONTROL_SERVICE,
  NEW_TASK_LINK_SERVICE as MAIN_NEW_TASK_LINK_SERVICE,
  OPEN_TARGET_LINK_SERVICE as MAIN_OPEN_TARGET_LINK_SERVICE,
  POSTHOG_PLUGIN_SERVICE as MAIN_POSTHOG_PLUGIN_SERVICE,
  PROCESS_TRACKING_SERVICE as MAIN_PROCESS_TRACKING_SERVICE,
  PROVISIONING_SERVICE as MAIN_PROVISIONING_SERVICE,
  REPOSITORY_REPOSITORY as MAIN_REPOSITORY_REPOSITORY,
  SCOUT_LINK_SERVICE as MAIN_SCOUT_LINK_SERVICE,
  SECURE_STORE_BACKEND as MAIN_SECURE_STORE_BACKEND,
  SECURE_STORE_SERVICE as MAIN_SECURE_STORE_SERVICE,
  SETTINGS_STORE as MAIN_SETTINGS_STORE,
  SLEEP_SERVICE as MAIN_SLEEP_SERVICE,
  SUSPENSION_REPOSITORY as MAIN_SUSPENSION_REPOSITORY,
  SUSPENSION_SERVICE as MAIN_SUSPENSION_SERVICE,
  TASK_LINK_SERVICE as MAIN_TASK_LINK_SERVICE,
  UPDATES_SERVICE as MAIN_UPDATES_SERVICE,
  WATCHER_REGISTRY_SERVICE as MAIN_WATCHER_REGISTRY_SERVICE,
  WORKSPACE_CLIENT as MAIN_WORKSPACE_CLIENT,
  WORKSPACE_REPOSITORY as MAIN_WORKSPACE_REPOSITORY,
  WORKSPACE_SERVER_SERVICE as MAIN_WORKSPACE_SERVER_SERVICE,
  WORKSPACE_SERVICE as MAIN_WORKSPACE_SERVICE,
  WORKTREE_REPOSITORY as MAIN_WORKTREE_REPOSITORY,
} from "./tokens";

async function cancelTaskSessions(
  agentService: AgentService,
  piSessionService: PiSessionService,
  taskId: string,
): Promise<void> {
  await Promise.all([
    agentService.cancelSessionsByTaskId(taskId),
    piSessionService.stop(taskId),
  ]);
}

export const container = new TypedContainer<MainBindings>({
  defaultScope: "Singleton",
});

container.bind(URL_LAUNCHER_SERVICE).to(ElectronUrlLauncher);
container.bind(SCREEN_CAPTURE_SERVICE).to(ElectronScreenCapture);
container.bind(STORAGE_PATHS_SERVICE).to(ElectronStoragePaths);
container.bind(APP_META_SERVICE).to(ElectronAppMeta);
container.bind(DIALOG_SERVICE).to(ElectronDialog);
container.bind(SETTINGS_BACKUP_FILES).to(ElectronSettingsBackupFiles);
container.bind(CLIPBOARD_SERVICE).to(ElectronClipboard);
container.bind(CRYPTO_SERVICE).to(ElectronCrypto);
container.bind(ANALYTICS_SERVICE).toConstantValue(posthogNodeAnalytics);
container.bind(FEEDBACK_CONTEXT_SERVICE).to(ElectronFeedbackContext);
container.bind(FILE_ICON_SERVICE).to(ElectronFileIcon);
container.bind(SECURE_STORAGE_SERVICE).to(ElectronSecureStorage);
container.bind(MAIN_WINDOW_SERVICE).to(ElectronMainWindow);
container.bind(APP_LIFECYCLE_SERVICE).to(ElectronAppLifecycle);
container.bind(POWER_MANAGER_SERVICE).to(ElectronPowerManager);
container.bind(UPDATER_SERVICE).to(ElectronUpdater);
container.bind(NOTIFIER_SERVICE).to(ElectronNotifier);
container.bind(CONTEXT_MENU_SERVICE).to(ElectronContextMenu);
container.bind(BUNDLED_RESOURCES_SERVICE).to(ElectronBundledResources);
container.bind(IMAGE_PROCESSOR_SERVICE).to(ElectronImageProcessor);
container.bind(WORKSPACE_SETTINGS_SERVICE).to(ElectronWorkspaceSettings);
container
  .bind(CUSTOM_CLOUD_STORE)
  .toConstantValue(new ElectronCustomCloudStore());
container.bind(APP_METRICS_SERVICE).to(ElectronAppMetrics);
container.bind(DEV_HOST_ACTIONS_SERVICE).to(ElectronDevHostActions);

container.load(databaseModule);
container.load(repositoriesModule);
container.bind(MAIN_DATABASE_SERVICE).toService(DATABASE_SERVICE);
container
  .bind(MAIN_AUTH_PREFERENCE_REPOSITORY)
  .toService(AUTH_PREFERENCE_REPOSITORY);
container.bind(MAIN_AUTH_SESSION_REPOSITORY).toService(AUTH_SESSION_REPOSITORY);
container.bind(MAIN_REPOSITORY_REPOSITORY).toService(REPOSITORY_REPOSITORY);
container.bind(MAIN_WORKSPACE_REPOSITORY).toService(WORKSPACE_REPOSITORY);
container.bind(MAIN_WORKTREE_REPOSITORY).toService(WORKTREE_REPOSITORY);
container.bind(MAIN_ARCHIVE_REPOSITORY).toService(ARCHIVE_REPOSITORY);
container.bind(MAIN_SUSPENSION_REPOSITORY).toService(SUSPENSION_REPOSITORY);
container
  .bind(MAIN_DEFAULT_ADDITIONAL_DIRECTORY_REPOSITORY)
  .toService(DEFAULT_ADDITIONAL_DIRECTORY_REPOSITORY);
container.load(agentModule);
container.bind(PI_RUNTIME_FACTORY).to(DesktopPiRuntimeFactory);
container.load(piSessionModule);
container.bind(AGENT_SLEEP_COORDINATOR).toService(MAIN_SLEEP_SERVICE);
container.bind(AGENT_MCP_APPS).toService(MCP_APPS_SERVICE);
container.bind(AGENT_REPO_FILES).toService(MAIN_FS_SERVICE);
container.bind(AGENT_AUTH).toService(MAIN_AUTH_SERVICE);
container
  .bind(PI_RPC_CLIENT_FACTORY)
  .to(DesktopPiRpcClientFactory)
  .inSingletonScope();
container.bind(AGENT_LOGGER).toConstantValue(logger);
container.load(osModule);
container.bind<RootLogger>(ROOT_LOGGER).toConstantValue(logger);
container.bind(AUTH_SESSION_STORE).to(AuthSessionPortAdapter);
container.bind(AUTH_PREFERENCE_STORE).to(AuthPreferencePortAdapter);
container.bind(AUTH_OAUTH_FLOW_SERVICE).to(OAuthFlowPortAdapter);
container.bind(AUTH_TOKEN_CIPHER).to(TokenCipherPortAdapter);
container
  .bind(WS_CONNECTIVITY_SERVICE)
  .to(ConnectivityService)
  .inSingletonScope();
container.bind(AUTH_CONNECTIVITY).toService(WS_CONNECTIVITY_SERVICE);
container.bind(CONNECTIVITY_CLIENT).toService(WS_CONNECTIVITY_SERVICE);
container
  .bind(AUTH_TOKEN_OVERRIDE)
  .toConstantValue(process.env.VITE_POSTHOG_ACCESS_TOKEN_OVERRIDE ?? null);
container
  .bind(AUTH_FETCH_EXTRA_ORIGINS)
  .toConstantValue(
    [process.env.POSTHOG_MCP_URL, process.env.POSTHOG_PROXY_BASE_URL].filter(
      (value): value is string => Boolean(value),
    ),
  );
container.bind(AUTH_FETCH).toConstantValue(electronNetFetch);
container.bind(MAIN_AUTH_SERVICE).to(AuthService);
container.bind(AUTH_SERVICE).toService(MAIN_AUTH_SERVICE);
container.load(feedbackCoreModule);
container.load(authProxyModule);
container.bind(AUTH_PROXY_AUTH).toDynamicValue((ctx) => ({
  authenticatedFetch: (url: string, init?: RequestInit) =>
    ctx
      .get<AuthService>(MAIN_AUTH_SERVICE)
      .authenticatedFetch(fetch, url, init),
}));
container
  .bind(GATEWAY_CREDENTIAL_SOURCE)
  .toDynamicValue((ctx) => ctx.get<GatewayTokenService>(GATEWAY_TOKEN_SERVICE));
container.load(mcpProxyModule);
container.bind(MCP_PROXY_AUTH).toDynamicValue((ctx) => {
  const auth = () => ctx.get<AuthService>(MAIN_AUTH_SERVICE);
  return {
    authenticatedFetch: (url: string, init?: RequestInit) =>
      auth().authenticatedFetch(fetch, url, init),
    refreshAccessToken: () => auth().refreshAccessToken(),
  };
});
container.load(archiveModule);
container.bind(ARCHIVE_SESSION_CANCELLER).toDynamicValue((ctx) => ({
  cancelSessionsByTaskId: (taskId: string) =>
    cancelTaskSessions(
      ctx.get<AgentService>(AGENT_SERVICE),
      ctx.get<PiSessionService>(PI_SESSION_SERVICE),
      taskId,
    ),
}));
container.bind(ARCHIVE_FILE_WATCHER).toDynamicValue((ctx) => ({
  stopWatching: async (worktreePath: string) => {
    ctx
      .get<FileWatcherBridge>(MAIN_FILE_WATCHER_SERVICE)
      .stopWatching(worktreePath);
  },
}));
container.load(suspensionModule);
container.bind(SUSPENSION_SESSION_CANCELLER).toDynamicValue((ctx) => ({
  cancelSessionsByTaskId: (taskId: string) =>
    cancelTaskSessions(
      ctx.get<AgentService>(AGENT_SERVICE),
      ctx.get<PiSessionService>(PI_SESSION_SERVICE),
      taskId,
    ),
}));
container.bind(SUSPENSION_FILE_WATCHER).toDynamicValue((ctx) => ({
  stopWatching: async (worktreePath: string) => {
    ctx
      .get<FileWatcherBridge>(MAIN_FILE_WATCHER_SERVICE)
      .stopWatching(worktreePath);
  },
}));
container.bind(MAIN_SUSPENSION_SERVICE).toService(SUSPENSION_SERVICE);
container.bind(MAIN_APP_LIFECYCLE_SERVICE).to(AppLifecycleService);
container.load(cloudTaskModule);
container.bind(CLOUD_TASK_AUTH).toDynamicValue((ctx) => ({
  authenticatedFetch: (url: string, init?: RequestInit) =>
    ctx
      .get<AuthService>(MAIN_AUTH_SERVICE)
      .authenticatedFetch(fetch, url, init),
  getCloudContext: async (options?: { includeAccount?: boolean }) => {
    const auth = ctx.get<AuthService>(MAIN_AUTH_SERVICE);
    const { apiHost } = await auth.getValidAccessToken();
    const teamId = auth.getState().currentProjectId;
    return teamId === null
      ? null
      : {
          apiHost,
          teamId,
          ...(options?.includeAccount && {
            accountKey: await auth.getAccountKey(),
          }),
        };
  },
}));
container.bind(MAIN_CLOUD_TASK_SERVICE).toService(CLOUD_TASK_SERVICE);
container.load(contextMenuCoreModule);
container
  .bind(CONTEXT_MENU_EXTERNAL_APPS_SERVICE)
  .toService(MAIN_EXTERNAL_APPS_SERVICE);
container.bind(MAIN_CONTEXT_MENU_SERVICE).toService(CONTEXT_MENU_CONTROLLER);
container.bind(MAIN_DEEP_LINK_SERVICE).to(DeepLinkService);
container.bind(DEEP_LINK_SERVICE).toService(MAIN_DEEP_LINK_SERVICE);
container.load(enrichmentModule);
container.bind(ENRICHMENT_AUTH).toDynamicValue((ctx) => {
  const auth = () => ctx.get<AuthService>(MAIN_AUTH_SERVICE);
  return {
    getState: () => {
      const state = auth().getState();
      return {
        status: state.status,
        projectId: state.currentProjectId ?? null,
        cloudRegion: state.cloudRegion ?? null,
      };
    },
    getValidAccessToken: async () => {
      const token = await auth().getValidAccessToken();
      return { accessToken: token.accessToken, apiHost: token.apiHost };
    },
  };
});
container.bind(ENRICHMENT_FILE_READER).toConstantValue({
  stat: (p: string) => fsStat(p).then((s) => ({ size: s.size })),
  readFile: (p: string) => fsReadFile(p, "utf-8"),
  listFilesContainingText: (repoPath: string, text: string) =>
    listFilesContainingText(repoPath, text),
});
container.bind(MAIN_PROVISIONING_SERVICE).to(ProvisioningService);
container.bind(PROVISIONING_SERVICE).toService(MAIN_PROVISIONING_SERVICE);

const externalAppsPrefsStore = new ExternalAppsStoreImpl<{
  externalAppsPrefs: ExternalAppsPreferences;
}>({
  name: "external-apps",
  cwd: getUserDataDir(),
  defaults: { externalAppsPrefs: {} },
});
container.bind(EXTERNAL_APPS_STORE).toConstantValue({
  getPrefs: () => externalAppsPrefsStore.get("externalAppsPrefs"),
  setPrefs: (prefs: ExternalAppsPreferences) =>
    externalAppsPrefsStore.set("externalAppsPrefs", prefs),
});
container.load(externalAppsModule);
container.bind(MAIN_EXTERNAL_APPS_SERVICE).toService(EXTERNAL_APPS_SERVICE);
container.load(llmGatewayModule);
container.bind(LLM_GATEWAY_HOST).toDynamicValue((ctx) => {
  const auth = () => ctx.get<AuthService>(MAIN_AUTH_SERVICE);
  return {
    getValidAccessToken: () => auth().getValidAccessToken(),
    authenticatedFetch: (url: string, init?: RequestInit) =>
      auth().authenticatedFetch(fetch, url, init),
    fetch: (url: string, init?: RequestInit) => fetch(url, init),
    messagesUrl: (apiHost: string) =>
      `${getLlmGatewayUrl(apiHost)}/v1/messages`,
    usageUrl: desktopUsageUrl,
    legacyUsageUrl: (apiHost: string) => getGatewayUsageUrl(apiHost),
    defaultModel: DEFAULT_GATEWAY_MODEL,
  };
});
container.bind(GATEWAY_TOKEN_HOST).toConstantValue(desktopGatewayTokenHost());
container.bind(MAIN_LLM_GATEWAY_SERVICE).toService(LLM_GATEWAY_SERVICE);
container.load(mcpAppsModule);
container.bind(MAIN_MCP_APPS_SERVICE).toService(MCP_APPS_SERVICE);
container.load(foldersModule);
container.load(integrationsModule);
container.load(gitPrModule);
container.bind(GIT_DIFF_SOURCE).toDynamicValue((ctx) => {
  const wsClient = () => ctx.get<HostGitWorkspaceClient>(GIT_WORKSPACE_CLIENT);
  const git = () => wsClient().git;
  return {
    getStagedDiff: (directoryPath: string) =>
      git().getDiffCached.query({ directoryPath }),
    getUnstagedDiff: (directoryPath: string) =>
      git().getDiffUnstaged.query({ directoryPath }),
    getCommitConventions: (directoryPath: string) =>
      git().getCommitConventions.query({ directoryPath }),
    getChangedFilesHead: (directoryPath: string) =>
      git().getChangedFilesHead.query({ directoryPath }),
    getDefaultBranch: (directoryPath: string) =>
      git().getDefaultBranch.query({ directoryPath }),
    getCurrentBranch: (directoryPath: string) =>
      git().getCurrentBranch.query({ directoryPath }),
    getDiffAgainstRemote: (directoryPath: string, baseBranch: string) =>
      git().getDiffAgainstRemote.query({ directoryPath, baseBranch }),
    getCommitsBetweenBranches: (
      directoryPath: string,
      baseBranch: string,
      head: string | undefined,
      limit: number,
    ) =>
      git().getCommitsBetweenBranches.query({
        directoryPath,
        baseBranch,
        head,
        limit,
      }),
    getPrTemplate: (directoryPath: string) =>
      git().getPrTemplate.query({ directoryPath }),
    fetchFromRemote: async (directoryPath: string) => {
      await git().getGitSyncStatus.query({
        directoryPath,
        fetchFromRemote: true,
      });
    },
  };
});
container
  .bind(GIT_AGENT_SERVICE)
  .toDynamicValue((ctx) => ctx.get<AgentService>(AGENT_SERVICE));
container
  .bind<GitWorkspaceLookup>(GIT_WORKSPACE_LOOKUP)
  .toDynamicValue((ctx): GitWorkspaceLookup => {
    const workspace = () => ctx.get<WorkspaceService>(WORKSPACE_SERVICE);
    return {
      getWorkspace: (taskId) => workspace().getWorkspace(taskId),
      linkBranch: (taskId, branch, source) =>
        workspace().linkBranch(taskId, branch, source),
    };
  });
container.load(gitHostModule);
container.bind(WS_GIT_SERVICE).to(GitService).inSingletonScope();
container
  .bind<IGitPrStatus>(GIT_PR_STATUS_PROVIDER)
  .to(TaskPrStatusService)
  .inSingletonScope();
container.load(mcpCallbackModule);
container.bind(NOTIFICATION_SERVICE).to(NotificationService);
container.load(oauthCallbackModule);
container.load(oauthModule);
container
  .bind(OAUTH_HOST)
  .toDynamicValue((ctx) => {
    const callback = ctx.get<OAuthCallbackReceiver>(OAUTH_CALLBACK_SERVER);
    return {
      waitForCode: callback.waitForCode.bind(callback),
      isDev: isDevBuild(),
    };
  })
  .inSingletonScope();
container.load(processTrackingModule);
container.load(workspaceMetadataModule);
container
  .bind(MAIN_PROCESS_TRACKING_SERVICE)
  .toService(PROCESS_TRACKING_SERVICE);
container.load(posthogPluginModule);
container.bind(MAIN_POSTHOG_PLUGIN_SERVICE).toService(POSTHOG_PLUGIN_SERVICE);
container.load(skillsModule);
container.load(skillsMarketplaceModule);
container.load(releaseFeedModule);
container.load(localMcpModule);
container.load(mcpRelayModule);
// Core's cloud-task service executes MCP relay requests through this seam;
// the workspace relay service satisfies the core executor interface
// structurally (docs/CLOUD-MCP-RELAY.md).
container
  .bind(MCP_RELAY_EXECUTOR)
  .toDynamicValue((ctx) => ctx.get(MCP_RELAY_SERVICE))
  .inSingletonScope();
container
  .bind(CLAUDE_SUBSCRIPTION_TOKEN_STORE)
  .toDynamicValue(
    (ctx) =>
      new ElectronClaudeSubscriptionTokenStore(
        join(getUserDataDir(), "claude-subscriptions"),
        () => ctx.get<AuthService>(MAIN_AUTH_SERVICE).getAccountKey(),
      ),
  )
  .inSingletonScope();
container.load(claudeCliSessionsModule);
container.load(additionalDirectoriesModule);
container.bind(MAIN_SLEEP_SERVICE).to(SleepService);
container.bind(SLEEP_SERVICE).toService(MAIN_SLEEP_SERVICE);
container.load(shellModule);
container.load(uiModule);
container.bind(UI_AUTH).toDynamicValue((ctx) => ({
  invalidateAccessTokenForTest: () =>
    ctx.get<AuthService>(MAIN_AUTH_SERVICE).invalidateAccessTokenForTest(),
}));
container.load(updatesCoreModule);
container.bind(UPDATE_LIFECYCLE_SERVICE).toService(MAIN_APP_LIFECYCLE_SERVICE);
container.bind(MAIN_UPDATES_SERVICE).toService(UPDATES_SERVICE);
container.load(usageMonitorModule);
container.bind(USAGE_HOST).toDynamicValue((ctx) => {
  const agent = () => ctx.get<AgentService>(AGENT_SERVICE);
  return {
    fetchUsage: () =>
      ctx.get<LlmGatewayService>(MAIN_LLM_GATEWAY_SERVICE).fetchUsage(),
    onLlmActivity: (listener: () => void) =>
      agent().on(AgentServiceEvent.LlmActivity, listener),
    offLlmActivity: (listener: () => void) =>
      agent().off(AgentServiceEvent.LlmActivity, listener),
    hasActiveSessions: () => agent().hasActiveSessions(),
    getThresholdsSeen: () => electronUsageThresholdStore.getThresholdsSeen(),
    setThresholdsSeen: (value: Record<string, string>) =>
      electronUsageThresholdStore.setThresholdsSeen(value),
  };
});
container.bind(MAIN_TASK_LINK_SERVICE).to(TaskLinkService);
container.bind(TASK_LINK_SERVICE).toService(MAIN_TASK_LINK_SERVICE);
container.bind(MAIN_INBOX_LINK_SERVICE).to(InboxLinkService);
container.bind(INBOX_LINK_SERVICE).toService(MAIN_INBOX_LINK_SERVICE);
container.bind(MAIN_SCOUT_LINK_SERVICE).to(ScoutLinkService);
container.bind(SCOUT_LINK_SERVICE).toService(MAIN_SCOUT_LINK_SERVICE);
container.bind(MAIN_NEW_TASK_LINK_SERVICE).to(NewTaskLinkService);
container.bind(NEW_TASK_LINK_SERVICE).toService(MAIN_NEW_TASK_LINK_SERVICE);
container.bind(MAIN_OPEN_TARGET_LINK_SERVICE).to(OpenTargetLinkService);
container
  .bind(OPEN_TARGET_LINK_SERVICE)
  .toService(MAIN_OPEN_TARGET_LINK_SERVICE);
container.bind(MAIN_CANVAS_LINK_SERVICE).to(CanvasLinkService);
container.bind(CANVAS_LINK_SERVICE).toService(MAIN_CANVAS_LINK_SERVICE);
container.bind(MAIN_CHANNEL_LINK_SERVICE).to(ChannelLinkService);
container.bind(CHANNEL_LINK_SERVICE).toService(MAIN_CHANNEL_LINK_SERVICE);
container.bind(MAIN_LOOP_LINK_SERVICE).to(LoopLinkService);
container.bind(LOOP_LINK_SERVICE).toService(MAIN_LOOP_LINK_SERVICE);
container.load(watcherRegistryModule);
container
  .bind(MAIN_WATCHER_REGISTRY_SERVICE)
  .toService(WATCHER_REGISTRY_SERVICE);
container.load(workspaceModule);
container.bind(WORKSPACE_AGENT).toDynamicValue((ctx): WorkspaceAgent => {
  const agent = ctx.get<AgentService>(AGENT_SERVICE);
  return {
    cancelSessionsByTaskId: (taskId) =>
      cancelTaskSessions(
        agent,
        ctx.get<PiSessionService>(PI_SESSION_SERVICE),
        taskId,
      ),
    onAgentFileActivity: (handler) =>
      agent.on(AgentServiceEvent.AgentFileActivity, handler),
  };
});
container
  .bind(WORKSPACE_FILE_WATCHER)
  .toDynamicValue((ctx): WorkspaceFileWatcher => {
    const fileWatcher = ctx.get<FileWatcherBridge>(MAIN_FILE_WATCHER_SERVICE);
    return {
      stopWatching: async (worktreePath) => {
        fileWatcher.stopWatching(worktreePath);
      },
      onGitStateChanged: (handler) =>
        fileWatcher.on(FileWatcherEventKind.GitStateChanged, (event) =>
          handler({ repoPath: event.repoPath }),
        ),
    };
  });
container.bind(WORKSPACE_FOCUS).toDynamicValue((ctx): WorkspaceFocus => {
  return {
    onBranchRenamed: (handler) =>
      ctx.get(FocusHostService).on(FocusServiceEvent.BranchRenamed, handler),
  };
});
container
  .bind(WORKSPACE_PROVISIONING)
  .toDynamicValue((ctx): WorkspaceProvisioning => {
    const provisioning = ctx.get<ProvisioningService>(
      MAIN_PROVISIONING_SERVICE,
    );
    return {
      emitOutput: (taskId, data) => provisioning.emitOutput(taskId, data),
    };
  });
container.bind(MAIN_WORKSPACE_SERVICE).toService(WORKSPACE_SERVICE);
container
  .bind(MAIN_WORKSPACE_SERVER_SERVICE)
  .to(WorkspaceServerService)
  .inSingletonScope();

container.bind(MAIN_SETTINGS_STORE).toConstantValue(settingsStore);

container.bind(MAIN_SECURE_STORE_BACKEND).toConstantValue(rendererStore);
container
  .bind(MAIN_SECURE_STORE_SERVICE)
  .to(SecureStoreService)
  .inSingletonScope();
container.bind(SECURE_STORE_SERVICE).toService(MAIN_SECURE_STORE_SERVICE);
container
  .bind(DISK_CACHE_SERVICE)
  .toDynamicValue(
    (ctx) =>
      new DiskCache({
        // Not "cache": userData already holds Chromium's "Cache" directory, and
        // case-insensitive file systems (default macOS, Windows) treat the two
        // as one path, so clear() would delete the live browser cache.
        rootDir: join(
          ctx.get<ElectronStoragePaths>(STORAGE_PATHS_SERVICE).appDataPath,
          "disk-cache",
        ),
      }),
  )
  .inSingletonScope();
container
  .bind(SPEECH_SYNTHESIZER_SERVICE)
  .to(ElevenLabsSpeechService)
  .inSingletonScope();
container.bind(LOGS_SERVICE).toDynamicValue((ctx) => {
  const ws = ctx.get<WorkspaceClient>(MAIN_WORKSPACE_CLIENT);
  return {
    fetchS3Logs: async (logUrl: string) => {
      try {
        const response = await fetch(logUrl);
        if (response.status === 404) return null;
        if (!response.ok) return null;
        return await response.text();
      } catch {
        return null;
      }
    },
    readLocalLogs: (taskRunId: string) =>
      ws.localLogs.read.query({ taskRunId }),
    readLocalLogsCollapsed: (taskRunId: string) =>
      ws.localLogs.readCollapsed.query({ taskRunId }),
    readLocalLogsTail: (taskRunId: string, maxBytes: number) =>
      ws.localLogs.readTail.query({ taskRunId, maxBytes }),
    writeLocalLogs: (taskRunId: string, content: string) =>
      ws.localLogs.write.mutate({ taskRunId, content }),
  };
});
container.bind(MAIN_ENCRYPTION_SERVICE).to(EncryptionService);
container.bind(MAIN_DISCORD_PRESENCE_SERVICE).to(DiscordPresenceService);
container.bind(MAIN_MISSION_CONTROL_SERVICE).to(MissionControlService);

// Canvas / dashboards (project-bluebird). The host-agnostic dashboard services
// live in @flind/core (bound via canvasCoreModule) and resolve through
// ctx.container in the host-router routers.
container.load(canvasCoreModule);

// Browser tabs for the Channels canvas surface. Authoritative sqlite-backed
// service in the main process; resolved by the host-router browserTabs router.
container.load(browserTabsModule);

container.bind(MAIN_DEV_FLAGS_SERVICE).to(DevFlagsService);
container.bind(MAIN_DEV_METRICS_SERVICE).to(DevMetricsService);
container.bind(MAIN_DEV_NETWORK_SERVICE).to(DevNetworkService);
container.bind(MAIN_DEV_LOGS_SERVICE).to(DevLogsService);
container.bind(MAIN_DEV_ACTIONS_SERVICE).to(DevActionsService);
