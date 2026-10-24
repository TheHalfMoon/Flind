import "reflect-metadata";
import { useDevFlagsStore } from "@features/dev-toolbar/devFlagsStore";
import { TypedContainer } from "@inversifyjs/strongly-typed";
import type { TrpcRouter } from "@main/trpc/router";
import { canvasApplicationModule } from "@flind/core/canvas/canvas.module";
import {
  CLOUD_TASK_CLIENT,
  type CloudTaskClient,
} from "@flind/core/cloud-task/cloudTaskClient";
import {
  CODE_REVIEW_WORKSPACE_CLIENT,
  REVERT_HUNK_SERVICE,
} from "@flind/core/code-review/identifiers";
import type { CodeReviewWorkspaceClient } from "@flind/core/code-review/revertHunkService";
import { RevertHunkService } from "@flind/core/code-review/revertHunkService";
import {
  GITHUB_ISSUE_CLIENT,
  type GitHubIssueClient,
  NEW_TASK_LINK_RESOLVER,
} from "@flind/core/deep-links/identifiers";
import { NewTaskLinkResolver } from "@flind/core/deep-links/newTaskLinkResolver";
import { ExternalAppService } from "@flind/core/external-apps/externalAppService";
import {
  EXTERNAL_APPS_FOCUS_COORDINATOR,
  EXTERNAL_APPS_SERVICE,
  EXTERNAL_APPS_WORKSPACE_CLIENT,
  type ExternalAppsWorkspaceClient,
} from "@flind/core/external-apps/identifiers";
import { FILE_READ_CLIENT } from "@flind/core/files/identifiers";
import { GitInteractionService } from "@flind/core/git-interaction/gitInteractionService";
import {
  GIT_INTERACTION_EFFECTS,
  GIT_INTERACTION_SERVICE,
  GIT_WRITE_CLIENT,
} from "@flind/core/git-interaction/identifiers";
import { LLM_GATEWAY_SERVICE } from "@flind/core/llm-gateway/identifiers";
import type { LlmGatewayService } from "@flind/core/llm-gateway/llm-gateway";
import type { LlmMessage } from "@flind/core/llm-gateway/schemas";
import { LOCAL_MCP_WORKSPACE_CLIENT } from "@flind/core/local-mcp/identifiers";
import type { LocalMcpWorkspaceClient } from "@flind/core/local-mcp/localMcpImport";
import { PI_RUNNER } from "@flind/core/pi-runtime/identifiers";
import { piRuntimeModule } from "@flind/core/pi-runtime/pi-runtime.module";
import type { PiRunner } from "@flind/core/pi-runtime/piRunner";
import { LOCAL_PI_SESSION_FACTORY } from "@flind/core/pi-runtime/piSessionController";
import {
  CLOUD_ARTIFACT_BUNDLE_LOCAL_SKILL,
  CLOUD_ARTIFACT_READ_FILE_AS_BASE64,
  CLOUD_ARTIFACT_RESOLVE_SKILL_DEPENDENCIES,
} from "@flind/core/sessions/cloudArtifactIdentifiers";
import {
  SESSION_SERVICE,
  type SessionService,
} from "@flind/core/sessions/sessionService";
import { sessionsModule } from "@flind/core/sessions/sessions.module";
import {
  TITLE_GENERATOR_GITHUB_PR_TITLE_CLIENT,
  TITLE_GENERATOR_LOGGER,
} from "@flind/core/sessions/titleGeneratorIdentifiers";
import { SKILLS_WORKSPACE_CLIENT } from "@flind/core/skills/identifiers";
import type { SkillsWorkspaceClient } from "@flind/core/skills/teamSkillsService";
import {
  TASK_CREATION_EFFECTS,
  TASK_CREATION_HOST,
  WORKSPACE_SETUP_SAGA,
} from "@flind/core/task-detail/identifiers";
import type { ITaskCreationHost } from "@flind/core/task-detail/taskCreationHost";
import {
  TASK_SERVICE,
  TaskService,
} from "@flind/core/task-detail/taskService";
import { WorkspaceSetupSaga } from "@flind/core/task-detail/workspaceSetupSaga";
import {
  TASK_DELETION_HOST,
  TASK_DELETION_SERVICE,
  TASK_DELETION_WORKSPACE_CLIENT,
} from "@flind/core/tasks/identifiers";
import { TaskDeletionService } from "@flind/core/tasks/taskDeletionService";
import {
  SHELL_PROCESS_READER,
  type ShellProcessReader,
} from "@flind/core/terminal/identifiers";
import { terminalCoreModule } from "@flind/core/terminal/terminal.module";
import {
  WORKSPACE_SETUP_GIT_CLIENT,
  WORKSPACE_SETUP_SERVICE,
} from "@flind/core/workspace/identifiers";
import { WorkspaceSetupService } from "@flind/core/workspace/WorkspaceSetupService";
import { setRootContainer } from "@flind/di/container";
import { HOST_TRPC_CLIENT } from "@flind/host-router/client";
import { TrpcCloudTaskClient } from "@flind/host-router/cloud-task-client";
import { TrpcPiRunner } from "@flind/host-router/pi-runner";
import { TrpcPiSessionFactory } from "@flind/host-router/pi-session-factory";
import {
  FEEDBACK_CONTEXT_SERVICE,
  type IFeedbackContext,
} from "@flind/platform/feedback-context";
import {
  type IScreenCapture,
  SCREEN_CAPTURE_SERVICE,
} from "@flind/platform/screen-capture";
import {
  BROWSER_TABS_CLIENT,
  type BrowserTabsClient,
} from "@flind/ui/features/browser-tabs/browserTabsClient";
import {
  REVIEW_HOST,
  type ReviewHost,
} from "@flind/ui/features/code-review/reviewHost";
import {
  CONNECTIVITY_CLIENT,
  type ConnectivityClient,
} from "@flind/ui/features/connectivity/connectivityClient";
import {
  DISCORD_PRESENCE_CLIENT,
  type DiscordPresenceClient,
} from "@flind/ui/features/discord-presence/identifiers";
import { FocusStoreCoordinator } from "@flind/ui/features/external-apps/focusCoordinator";
import { focusDeps } from "@flind/ui/features/focus/focusAdapter";
import { FOCUS_CONTROLLER_DEPS } from "@flind/ui/features/focus/focusClient";
import {
  gitInteractionEffects,
  gitWriteClient,
} from "@flind/ui/features/git-interaction/gitInteractionAdapter";
import { McpAppHost } from "@flind/ui/features/mcp-apps/components/McpAppHost";
import { McpToolBlock } from "@flind/ui/features/mcp-apps/components/McpToolBlock";
import {
  MCP_APP_HOST_COMPONENT,
  MCP_SANDBOX_PROXY_URL,
} from "@flind/ui/features/mcp-apps/identifiers";
import {
  MISSION_CONTROL_CLIENT,
  type MissionControlClient,
} from "@flind/ui/features/mission-control/identifiers";
import { ARTIFACT_HTML_FRAME_COMPONENT } from "@flind/ui/features/sessions/components/artifactHtmlFrameHost";
import { MCP_TOOL_BLOCK_COMPONENT } from "@flind/ui/features/sessions/components/session-update/identifiers";
import { getSessionService } from "@flind/ui/features/sessions/sessionServiceHost";
import {
  DEV_MODE_CLIENT,
  type DevModeClient,
} from "@flind/ui/features/settings/devModeClient";
import { taskCreationEffects } from "@flind/ui/features/task-detail/taskCreationEffectsImpl";
import { TrpcTaskCreationHost } from "@flind/ui/features/task-detail/taskCreationHostImpl";
import {
  SHELL_CLIENT,
  type ShellClient,
} from "@flind/ui/features/terminal/shellClient";
import { updatesClient } from "@flind/ui/features/updates/updatesAdapter";
import { UPDATES_CLIENT } from "@flind/ui/features/updates/updatesClient";
import {
  ANALYTICS_TRACKER,
  type AnalyticsTracker,
} from "@flind/ui/shell/analytics";
import { DIFF_WORKER_FACTORY } from "@flind/ui/shell/diffWorkerHost";
import { HOST_LOGGER } from "@flind/ui/shell/logger";
import { posthogAnalyticsTracker } from "@flind/ui/shell/posthogAnalyticsImpl";
import {
  diffWorkerFactory,
  reviewHost,
} from "@renderer/features/code-review/reviewHost";
import { ElectronArtifactHtmlFrame } from "@renderer/platform-adapters/electron-artifact-html-frame";
import {
  taskDeletionHost,
  taskDeletionWorkspaceClient,
} from "@renderer/platform-adapters/task-deletion";
import { trpcClient } from "@renderer/trpc";
import { hostTrpcClient } from "@renderer/trpc/client";
import type { TRPCClient } from "@trpc/client";
import { hostLog, logger } from "@utils/logger";
import type { RendererBindings } from "./bindings";
import { TASK_SERVICE as RENDERER_TASK_SERVICE, TRPC_CLIENT } from "./tokens";

/**
 * Renderer process dependency injection container
 */
export const container = new TypedContainer<RendererBindings>({
  defaultScope: "Singleton",
});

setRootContainer(container);

container.bind(HOST_LOGGER).toConstantValue(hostLog);

// Bind infrastructure
container.bind<TRPCClient<TrpcRouter>>(TRPC_CLIENT).toConstantValue(trpcClient);

container.bind(HOST_TRPC_CLIENT).toConstantValue(hostTrpcClient);

container.bind(SCREEN_CAPTURE_SERVICE).toConstantValue({
  captureRegion: (region) =>
    hostTrpcClient.screenCapture.captureRegion.query(region),
} satisfies IScreenCapture);
container.bind(FEEDBACK_CONTEXT_SERVICE).toConstantValue({
  captureScreenshot: () =>
    hostTrpcClient.feedbackContext.captureScreenshot.query(),
  readRecentLogs: () => hostTrpcClient.feedbackContext.readRecentLogs.query(),
  submitFeedback: (input) =>
    hostTrpcClient.feedbackContext.submitFeedback.mutate(input),
} satisfies IFeedbackContext);

container.bind(UPDATES_CLIENT).toConstantValue(updatesClient);

// dev mode client — exposes the dev-toolbar flag store to the shared settings UI
const devModeClient: DevModeClient = {
  getDevMode: () => useDevFlagsStore.getState().devMode,
  setDevMode: (enabled) => useDevFlagsStore.getState().setDevMode(enabled),
  onDevModeChanged: (listener) =>
    useDevFlagsStore.subscribe((state) => listener(state.devMode)),
};
container.bind(DEV_MODE_CLIENT).toConstantValue(devModeClient);

// connectivity client — passthrough over the renderer host client
const connectivityClient: ConnectivityClient = {
  getStatus: () => trpcClient.connectivity.getStatus.query(),
  checkNow: () => trpcClient.connectivity.checkNow.mutate(),
  onStatusChange: (sub) =>
    trpcClient.connectivity.onStatusChange.subscribe(undefined, sub),
};
container.bind(CONNECTIVITY_CLIENT).toConstantValue(connectivityClient);

// browser tabs client — passthrough over the renderer host client
const browserTabsClient: BrowserTabsClient = {
  getSnapshot: () => trpcClient.browserTabs.getSnapshot.query(),
  getPrimaryWindowId: () => trpcClient.browserTabs.getPrimaryWindowId.query(),
  reset: () => trpcClient.browserTabs.reset.mutate(),
  openTab: (input) => trpcClient.browserTabs.openTab.mutate(input),
  setTabTarget: (input) => trpcClient.browserTabs.setTabTarget.mutate(input),
  close: (tabId, newTabId) =>
    trpcClient.browserTabs.close.mutate({ tabId, newTabId }),
  closeMany: (input) => trpcClient.browserTabs.closeMany.mutate(input),
  setOrder: (input) => trpcClient.browserTabs.setOrder.mutate(input),
  setActiveTab: (input) => trpcClient.browserTabs.setActiveTab.mutate(input),
  onSnapshotChange: (sub) =>
    trpcClient.browserTabs.onSnapshotChange.subscribe(undefined, sub),
};
container.bind(BROWSER_TABS_CLIENT).toConstantValue(browserTabsClient);

// discord presence client — passthrough over the local main-process router
const discordPresenceClient: DiscordPresenceClient = {
  getState: () => trpcClient.discordPresence.getState.query(),
  setEnabled: async (enabled) => {
    await trpcClient.discordPresence.setEnabled.mutate({ enabled });
  },
  setShowTaskTitle: async (value) => {
    await trpcClient.discordPresence.setShowTaskTitle.mutate({ value });
  },
  setShowRepoName: async (value) => {
    await trpcClient.discordPresence.setShowRepoName.mutate({ value });
  },
  setActivity: async (intent) => {
    await trpcClient.discordPresence.setActivity.mutate(intent);
  },
  onStatusChanged: (onData) => {
    const sub = trpcClient.discordPresence.onStatusChanged.subscribe(
      undefined,
      { onData },
    );
    return () => sub.unsubscribe();
  },
};
container.bind(DISCORD_PRESENCE_CLIENT).toConstantValue(discordPresenceClient);

// mission control overlay client
const missionControlClient: MissionControlClient = {
  onStateChanged: (onData) => {
    const sub = trpcClient.missionControl.onStateChanged.subscribe(undefined, {
      onData,
    });
    return () => sub.unsubscribe();
  },
  isSupported: () => trpcClient.missionControl.isSupported.query(),
  getEnabled: () => trpcClient.missionControl.getEnabled.query(),
  setEnabled: (enabled) =>
    trpcClient.missionControl.setEnabled.mutate({ enabled }),
};
container.bind(MISSION_CONTROL_CLIENT).toConstantValue(missionControlClient);

// terminal shell client
const shellClient: ShellClient = {
  write: async (input) => {
    await trpcClient.shell.write.mutate(input);
  },
  check: (input) => trpcClient.shell.check.query(input),
  destroy: async (input) => {
    await trpcClient.shell.destroy.mutate(input);
  },
  create: async (input) => {
    await trpcClient.shell.create.mutate(input);
  },
  createCommand: async (input) => {
    await trpcClient.shell.createCommand.mutate(input);
  },
  resize: async (input) => {
    await trpcClient.shell.resize.mutate(input);
  },
  getProcess: async (input) =>
    (await trpcClient.shell.getProcess.query(input)) ?? null,
  execute: (input) => trpcClient.shell.execute.mutate(input),
  openExternal: async (input) => {
    await trpcClient.os.openExternal.mutate(input);
  },
  onData: (sessionId, onEvent) =>
    trpcClient.shell.onData.subscribe({ sessionId }, { onData: onEvent }),
  onExit: (sessionId, onEvent) =>
    trpcClient.shell.onExit.subscribe({ sessionId }, { onData: onEvent }),
};
container.bind(SHELL_CLIENT).toConstantValue(shellClient);

// focus controller deps
container.bind(FOCUS_CONTROLLER_DEPS).toConstantValue(focusDeps);

// code-review host (diff worker factory + expanded-review sidebar)
container.bind(DIFF_WORKER_FACTORY).toConstantValue(diffWorkerFactory);
container.bind<ReviewHost>(REVIEW_HOST).toConstantValue(reviewHost);

container
  .bind(ARTIFACT_HTML_FRAME_COMPONENT)
  .toConstantValue(ElectronArtifactHtmlFrame);

// sessions MCP tool renderer slot
container.bind(MCP_TOOL_BLOCK_COMPONENT).toConstantValue(McpToolBlock);

// interactive MCP App iframe host + its electron isolated-origin sandbox URL
container.bind(MCP_APP_HOST_COMPONENT).toConstantValue(McpAppHost);
container
  .bind(MCP_SANDBOX_PROXY_URL)
  .toConstantValue(() => "mcp-sandbox://proxy");

// terminal shell process reader + core module
container.bind<ShellProcessReader>(SHELL_PROCESS_READER).toConstantValue({
  getProcess: async (input) =>
    (await trpcClient.shell.getProcess.query(input)) ?? null,
});
container.load(terminalCoreModule);

// analytics tracker
container
  .bind<AnalyticsTracker>(ANALYTICS_TRACKER)
  .toConstantValue(posthogAnalyticsTracker);

// Bind services
container.bind<ITaskCreationHost>(TASK_CREATION_HOST).to(TrpcTaskCreationHost);
container.bind<PiRunner>(PI_RUNNER).to(TrpcPiRunner);
container.bind(LOCAL_PI_SESSION_FACTORY).to(TrpcPiSessionFactory);
container.bind<CloudTaskClient>(CLOUD_TASK_CLIENT).to(TrpcCloudTaskClient);
container.load(piRuntimeModule);
container.bind(TASK_CREATION_EFFECTS).toConstantValue(taskCreationEffects);
container.bind<TaskService>(RENDERER_TASK_SERVICE).to(TaskService);
container.bind<TaskService>(TASK_SERVICE).toService(RENDERER_TASK_SERVICE);
container
  .bind<WorkspaceSetupSaga>(WORKSPACE_SETUP_SAGA)
  .to(WorkspaceSetupSaga)
  .inSingletonScope();
container
  .bind<SessionService>(SESSION_SERVICE)
  .toDynamicValue(() => getSessionService())
  .inSingletonScope();
// git-interaction
container.bind(GIT_WRITE_CLIENT).toConstantValue(gitWriteClient);
container.bind(GIT_INTERACTION_EFFECTS).toConstantValue(gitInteractionEffects);
container
  .bind(GIT_INTERACTION_SERVICE)
  .to(GitInteractionService)
  .inSingletonScope();

// tasks (deletion)
container
  .bind(TASK_DELETION_WORKSPACE_CLIENT)
  .toConstantValue(taskDeletionWorkspaceClient);
container.bind(TASK_DELETION_HOST).toConstantValue(taskDeletionHost);
container
  .bind<TaskDeletionService>(TASK_DELETION_SERVICE)
  .to(TaskDeletionService)
  .inSingletonScope();

// external-apps
container.bind(EXTERNAL_APPS_WORKSPACE_CLIENT).toConstantValue({
  openInApp: (appId: string, targetPath: string) =>
    hostTrpcClient.externalApps.openInApp.mutate({ appId, targetPath }),
  setLastUsed: async (appId: string) => {
    await hostTrpcClient.externalApps.setLastUsed.mutate({ appId });
  },
  getDetectedApps: () => hostTrpcClient.externalApps.getDetectedApps.query(),
  copyPath: async (targetPath: string) => {
    await hostTrpcClient.externalApps.copyPath.mutate({ targetPath });
  },
} satisfies ExternalAppsWorkspaceClient);
container
  .bind(EXTERNAL_APPS_FOCUS_COORDINATOR)
  .to(FocusStoreCoordinator)
  .inSingletonScope();
container.bind(EXTERNAL_APPS_SERVICE).to(ExternalAppService).inSingletonScope();

// workspace setup
container.bind(WORKSPACE_SETUP_GIT_CLIENT).toConstantValue({
  detectRepo: (args: { directoryPath: string }) =>
    trpcClient.git.detectRepo.query(args),
});
container
  .bind(WORKSPACE_SETUP_SERVICE)
  .to(WorkspaceSetupService)
  .inSingletonScope();

// deep-links
container.bind(GITHUB_ISSUE_CLIENT).toConstantValue({
  getGithubIssue: (owner, repo, issueNumber) =>
    trpcClient.git.getGithubIssue.query({
      owner,
      repo,
      number: issueNumber,
    }),
} satisfies GitHubIssueClient);
container
  .bind(NEW_TASK_LINK_RESOLVER)
  .to(NewTaskLinkResolver)
  .inSingletonScope();

// code-review
container.bind(CODE_REVIEW_WORKSPACE_CLIENT).toConstantValue({
  getFileAtHead: (directoryPath: string, filePath: string) =>
    trpcClient.git.getFileAtHead.query({ directoryPath, filePath }),
  readRepoFile: (repoPath: string, filePath: string) =>
    trpcClient.fs.readRepoFile.query({ repoPath, filePath }),
  writeRepoFile: async (
    repoPath: string,
    filePath: string,
    content: string,
  ) => {
    await trpcClient.fs.writeRepoFile.mutate({ repoPath, filePath, content });
  },
} satisfies CodeReviewWorkspaceClient);
container.bind(REVERT_HUNK_SERVICE).to(RevertHunkService).inSingletonScope();

// local MCP servers (~/.claude.json), read for cloud-import classification
container.bind(LOCAL_MCP_WORKSPACE_CLIENT).toConstantValue({
  listLocalMcpServers: (cwd?: string) =>
    trpcClient.localMcp.list.query({ cwd }),
} satisfies LocalMcpWorkspaceClient);

// skills (team publish/install reach workspace-server through this slice)
container.bind(SKILLS_WORKSPACE_CLIENT).toConstantValue({
  exportSkill: (skillPath: string) =>
    trpcClient.skills.export.query({ skillPath }),
  installTeamSkill: (input) => trpcClient.skills.installTeamSkill.mutate(input),
} satisfies SkillsWorkspaceClient);

// sessions (cloud-artifact + title-generator)
container.load(sessionsModule);

// canvas generation orchestration (deps: task service, model resolver, title
// generator — all renderer-bound; persistence effects come in via its gateway)
container.load(canvasApplicationModule);
container
  .bind(CLOUD_ARTIFACT_READ_FILE_AS_BASE64)
  .toConstantValue((filePath: string) =>
    trpcClient.fs.readFileAsBase64.query({ filePath }),
  );
container
  .bind(CLOUD_ARTIFACT_BUNDLE_LOCAL_SKILL)
  .toConstantValue((skillBundleRef) =>
    hostTrpcClient.skills.bundleLocal.query(skillBundleRef),
  );
container
  .bind(CLOUD_ARTIFACT_RESOLVE_SKILL_DEPENDENCIES)
  .toConstantValue((skillBundleRefs) =>
    hostTrpcClient.skills.resolveDependencies.query(skillBundleRefs),
  );
container.bind(LLM_GATEWAY_SERVICE).toConstantValue({
  prompt: (
    messages: LlmMessage[],
    options: { system?: string; maxTokens?: number; model?: string } = {},
  ) =>
    trpcClient.llmGateway.prompt.mutate({
      messages,
      system: options.system,
      maxTokens: options.maxTokens,
      model: options.model,
    }),
} as unknown as LlmGatewayService);
container.bind(FILE_READ_CLIENT).toConstantValue({
  readAbsoluteFile: (filePath: string) =>
    trpcClient.fs.readAbsoluteFile.query({ filePath }),
});
container.bind(TITLE_GENERATOR_GITHUB_PR_TITLE_CLIENT).toConstantValue({
  getGithubPullRequestTitle: async (input) =>
    (await hostTrpcClient.git.getGithubPullRequest.query(input))?.title ?? null,
});
container
  .bind(TITLE_GENERATOR_LOGGER)
  .toConstantValue(logger.scope("title-generator"));
