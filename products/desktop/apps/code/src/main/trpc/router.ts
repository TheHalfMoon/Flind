import type { HostRouter } from "@flind/host-router/router";
import { additionalDirectoriesRouter } from "@flind/host-router/routers/additional-directories.router";
import { agentRouter } from "@flind/host-router/routers/agent.router";
import { analyticsRouter } from "@flind/host-router/routers/analytics.router";
import { archiveRouter } from "@flind/host-router/routers/archive.router";
import { authRouter } from "@flind/host-router/routers/auth.router";
import { autoresearchRouter } from "@flind/host-router/routers/autoresearch.router";
import { browserTabsRouter } from "@flind/host-router/routers/browser-tabs.router";
import { canvasDataRouter } from "@flind/host-router/routers/canvas-data.router";
import { canvasTemplatesRouter } from "@flind/host-router/routers/canvas-templates.router";
import { channelTasksRouter } from "@flind/host-router/routers/channel-tasks.router";
import { claudeCliSessionsRouter } from "@flind/host-router/routers/claude-cli-sessions.router";
import { claudeSubscriptionTokenRouter } from "@flind/host-router/routers/claude-subscription-token.router";
import { cloudTaskRouter } from "@flind/host-router/routers/cloud-task.router";
import { connectivityRouter } from "@flind/host-router/routers/connectivity.router";
import { contextMenuRouter } from "@flind/host-router/routers/context-menu.router";
import { customCloudRouter } from "@flind/host-router/routers/custom-cloud.router";
import { dashboardsRouter } from "@flind/host-router/routers/dashboards.router";
import { deepLinkRouter } from "@flind/host-router/routers/deep-link.router";
import { diskCacheRouter } from "@flind/host-router/routers/disk-cache.router";
import { enrichmentRouter } from "@flind/host-router/routers/enrichment.router";
import { environmentRouter } from "@flind/host-router/routers/environment.router";
import { externalAppsRouter } from "@flind/host-router/routers/external-apps.router";
import { feedbackContextRouter } from "@flind/host-router/routers/feedback-context.router";
import { fileWatcherRouter } from "@flind/host-router/routers/file-watcher.router";
import { focusRouter } from "@flind/host-router/routers/focus.router";
import { foldersRouter } from "@flind/host-router/routers/folders.router";
import { fsRouter } from "@flind/host-router/routers/fs.router";
import { gitRouter } from "@flind/host-router/routers/git.router";
import { githubIntegrationRouter } from "@flind/host-router/routers/github-integration.router";
import { integrationRouter } from "@flind/host-router/routers/integration.router";
import { linearIntegrationRouter } from "@flind/host-router/routers/linear-integration.router";
import { llmGatewayRouter } from "@flind/host-router/routers/llm-gateway.router";
import { localMcpRouter } from "@flind/host-router/routers/local-mcp.router";
import { logsRouter } from "@flind/host-router/routers/logs.router";
import { mcpAppsRouter } from "@flind/host-router/routers/mcp-apps.router";
import { mcpCallbackRouter } from "@flind/host-router/routers/mcp-callback.router";
import { mcpRelayRouter } from "@flind/host-router/routers/mcp-relay.router";
import { notificationRouter } from "@flind/host-router/routers/notification.router";
import { oauthRouter } from "@flind/host-router/routers/oauth.router";
import { osRouter } from "@flind/host-router/routers/os.router";
import { piSessionRouter } from "@flind/host-router/routers/pi-session.router";
import { processTrackingRouter } from "@flind/host-router/routers/process-tracking.router";
import { provisioningRouter } from "@flind/host-router/routers/provisioning.router";
import { releaseFeedRouter } from "@flind/host-router/routers/release-feed.router";
import { screenCaptureRouter } from "@flind/host-router/routers/screen-capture.router";
import { secureStoreRouter } from "@flind/host-router/routers/secure-store.router";
import { settingsBackupRouter } from "@flind/host-router/routers/settings-backup.router";
import { shellRouter } from "@flind/host-router/routers/shell.router";
import { skillsRouter } from "@flind/host-router/routers/skills.router";
import { slackIntegrationRouter } from "@flind/host-router/routers/slack-integration.router";
import { sleepRouter } from "@flind/host-router/routers/sleep.router";
import { speechRouter } from "@flind/host-router/routers/speech.router";
import { suspensionRouter } from "@flind/host-router/routers/suspension.router";
import { uiRouter } from "@flind/host-router/routers/ui.router";
import { updatesRouter } from "@flind/host-router/routers/updates.router";
import { usageMonitorRouter } from "@flind/host-router/routers/usage-monitor.router";
import { workspaceRouter } from "@flind/host-router/routers/workspace.router";
import { devRouter } from "./routers/dev";
import { discordPresenceRouter } from "./routers/discord-presence";
import { encryptionRouter } from "./routers/encryption";
import { missionControlRouter } from "./routers/mission-control";
import { workspaceServerRouter } from "./routers/workspace-server";
import { router } from "./trpc";

export const trpcRouter = router({
  additionalDirectories: additionalDirectoriesRouter,
  agent: agentRouter,
  analytics: analyticsRouter,
  archive: archiveRouter,
  auth: authRouter,
  autoresearch: autoresearchRouter,
  browserTabs: browserTabsRouter,
  canvasData: canvasDataRouter,
  canvasTemplates: canvasTemplatesRouter,
  channelTasks: channelTasksRouter,
  claudeCliSessions: claudeCliSessionsRouter,
  dashboards: dashboardsRouter,
  cloudTask: cloudTaskRouter,
  connectivity: connectivityRouter,
  contextMenu: contextMenuRouter,
  customCloud: customCloudRouter,
  dev: devRouter,
  discordPresence: discordPresenceRouter,
  enrichment: enrichmentRouter,
  environment: environmentRouter,
  encryption: encryptionRouter,
  externalApps: externalAppsRouter,
  feedbackContext: feedbackContextRouter,
  screenCapture: screenCaptureRouter,
  fileWatcher: fileWatcherRouter,
  focus: focusRouter,
  folders: foldersRouter,
  fs: fsRouter,
  git: gitRouter,
  githubIntegration: githubIntegrationRouter,
  releaseFeed: releaseFeedRouter,
  integration: integrationRouter,
  linearIntegration: linearIntegrationRouter,
  llmGateway: llmGatewayRouter,
  localMcp: localMcpRouter,
  mcpApps: mcpAppsRouter,
  mcpCallback: mcpCallbackRouter,
  mcpRelay: mcpRelayRouter,
  missionControl: missionControlRouter,
  notification: notificationRouter,
  oauth: oauthRouter,
  logs: logsRouter,
  os: osRouter,
  settingsBackup: settingsBackupRouter,
  piSession: piSessionRouter,
  processTracking: processTrackingRouter,
  provisioning: provisioningRouter,
  sleep: sleepRouter,
  suspension: suspensionRouter,
  secureStore: secureStoreRouter,
  claudeSubscriptionToken: claudeSubscriptionTokenRouter,
  shell: shellRouter,
  speech: speechRouter,
  skills: skillsRouter,
  slackIntegration: slackIntegrationRouter,
  ui: uiRouter,
  updates: updatesRouter,
  usageMonitor: usageMonitorRouter,
  deepLink: deepLinkRouter,
  diskCache: diskCacheRouter,
  workspace: workspaceRouter,
  workspaceServer: workspaceServerRouter,
});

export type TrpcRouter = typeof trpcRouter;

/**
 * The renderer and @flind/ui are typed against HostRouter, so every route it
 * declares must actually be served by this assembly — a route present in the
 * type but missing here fails only at runtime with NOT_FOUND, which is how a
 * route has been dropped before and silently broken the feature behind it.
 * When this assignment errors, its expected type names the missing routes.
 */
type MissingHostRoutes = Exclude<keyof HostRouter, keyof TrpcRouter>;
true satisfies [MissingHostRoutes] extends [never] ? true : MissingHostRoutes;
