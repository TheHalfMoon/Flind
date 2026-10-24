import type { TrpcRouter } from "@main/trpc/router";
import {
  ARCHIVE_CLIENT,
  type ArchiveClient,
} from "@flind/core/archive/identifiers";
import type { AutoresearchService } from "@flind/core/autoresearch/autoresearch";
import {
  AUTORESEARCH_GATE,
  AUTORESEARCH_SERVICE,
  AUTORESEARCH_SESSION_CLIENT,
  AUTORESEARCH_STORAGE_CLIENT,
  type AutoresearchGate,
  type AutoresearchSessionClient,
  type AutoresearchStorageClient,
} from "@flind/core/autoresearch/identifiers";
import {
  CLOUD_TASK_CLIENT,
  type CloudTaskClient,
} from "@flind/core/cloud-task/cloudTaskClient";
import {
  CODE_REVIEW_WORKSPACE_CLIENT,
  REVERT_HUNK_SERVICE,
} from "@flind/core/code-review/identifiers";
import type {
  CodeReviewWorkspaceClient,
  RevertHunkService,
} from "@flind/core/code-review/revertHunkService";
import {
  GITHUB_ISSUE_CLIENT,
  type GitHubIssueClient,
  NEW_TASK_LINK_RESOLVER,
} from "@flind/core/deep-links/identifiers";
import type { NewTaskLinkResolver } from "@flind/core/deep-links/newTaskLinkResolver";
import type { ReadFileAsBase64 } from "@flind/core/editor/cloud-prompt";
import type { ExternalAppService } from "@flind/core/external-apps/externalAppService";
import {
  EXTERNAL_APPS_FOCUS_COORDINATOR,
  EXTERNAL_APPS_SERVICE,
  EXTERNAL_APPS_WORKSPACE_CLIENT,
  type ExternalAppsWorkspaceClient,
} from "@flind/core/external-apps/identifiers";
import {
  FILE_READ_CLIENT,
  type FileReadClient,
} from "@flind/core/files/identifiers";
import type {
  GitInteractionEffects,
  GitInteractionService,
  IGitWriteClient,
} from "@flind/core/git-interaction/gitInteractionService";
import {
  GIT_INTERACTION_EFFECTS,
  GIT_INTERACTION_SERVICE,
  GIT_WRITE_CLIENT,
} from "@flind/core/git-interaction/identifiers";
import {
  LINEAR_OAUTH_FLOW,
  type LinearOAuthFlow,
  REPORT_MODEL_RESOLVER,
  type ReportModelResolver,
} from "@flind/core/inbox/identifiers";
import {
  CODEX_CLOUD_ACCOUNT_HOST,
  type CodexCloudAccountHost,
} from "@flind/core/integrations/codexCloudAccountService";
import {
  GITHUB_CONNECT_CLIENT as INTEGRATIONS_GITHUB_CONNECT_CLIENT,
  type GithubConnectClient as IntegrationsGithubConnectClient,
  REPOSITORIES_CLIENT,
  REPOSITORIES_SERVICE,
  type RepositoriesClient,
} from "@flind/core/integrations/identifiers";
import type { RepositoriesService } from "@flind/core/integrations/repositoriesService";
import { LLM_GATEWAY_SERVICE } from "@flind/core/llm-gateway/identifiers";
import type { LlmGatewayService } from "@flind/core/llm-gateway/llm-gateway";
import {
  LOCAL_MCP_IMPORT_SERVICE,
  LOCAL_MCP_WORKSPACE_CLIENT,
} from "@flind/core/local-mcp/identifiers";
import type {
  LocalMcpImportService,
  LocalMcpWorkspaceClient,
} from "@flind/core/local-mcp/localMcpImport";
import {
  GITHUB_CONNECT_CLIENT,
  type GithubConnectClient,
} from "@flind/core/onboarding/identifiers";
import { PI_RUNNER } from "@flind/core/pi-runtime/identifiers";
import type { PiRunner } from "@flind/core/pi-runtime/piRunner";
import {
  LOCAL_PI_SESSION_FACTORY,
  PI_SESSION_PROVIDER,
  type PiSessionFactory,
  type PiSessionProvider,
} from "@flind/core/pi-runtime/piSessionController";
import {
  type BundleLocalSkill,
  CLOUD_ARTIFACT_BUNDLE_LOCAL_SKILL,
  CLOUD_ARTIFACT_READ_FILE_AS_BASE64,
  CLOUD_ARTIFACT_RESOLVE_SKILL_DEPENDENCIES,
  type ResolveSkillBundleDependencies,
} from "@flind/core/sessions/cloudArtifactIdentifiers";
import {
  SESSION_SERVICE,
  type SessionService,
} from "@flind/core/sessions/sessionService";
import type {
  GithubPrTitleClient,
  TitleGeneratorLogger,
} from "@flind/core/sessions/titleGeneratorIdentifiers";
import {
  TITLE_GENERATOR_GITHUB_PR_TITLE_CLIENT,
  TITLE_GENERATOR_LOGGER,
} from "@flind/core/sessions/titleGeneratorIdentifiers";
import { type ISetupStore, SETUP_STORE } from "@flind/core/setup/identifiers";
import { SKILLS_WORKSPACE_CLIENT } from "@flind/core/skills/identifiers";
import type { SkillsWorkspaceClient } from "@flind/core/skills/teamSkillsService";
import {
  SPEECH_SETTINGS_PROVIDER,
  SPEECH_USER_NAME_PROVIDER,
  type SpeechSettingsProvider,
  type UserNameProvider,
} from "@flind/core/speech/identifiers";
import {
  TASK_CREATION_EFFECTS,
  TASK_CREATION_HOST,
  WORKSPACE_SETUP_SAGA,
} from "@flind/core/task-detail/identifiers";
import type { TaskCreationEffects } from "@flind/core/task-detail/taskCreationEffects";
import type { ITaskCreationHost } from "@flind/core/task-detail/taskCreationHost";
import {
  TASK_SERVICE,
  type TaskService,
} from "@flind/core/task-detail/taskService";
import type { WorkspaceSetupSaga } from "@flind/core/task-detail/workspaceSetupSaga";
import {
  type ITaskDeletionHost,
  type ITaskDeletionWorkspaceClient,
  TASK_DELETION_HOST,
  TASK_DELETION_SERVICE,
  TASK_DELETION_WORKSPACE_CLIENT,
} from "@flind/core/tasks/identifiers";
import type { TaskDeletionService } from "@flind/core/tasks/taskDeletionService";
import {
  SHELL_PROCESS_READER,
  type ShellProcessReader,
} from "@flind/core/terminal/identifiers";
import {
  WORKSPACE_SETUP_GIT_CLIENT,
  WORKSPACE_SETUP_SERVICE,
  type WorkspaceSetupGitClient,
} from "@flind/core/workspace/identifiers";
import type { WorkspaceSetupService } from "@flind/core/workspace/WorkspaceSetupService";
import { CONTRIBUTION, type Contribution } from "@flind/di/contribution";
import { ROOT_LOGGER, type RootLogger } from "@flind/di/logger";
import {
  HOST_TRPC_CLIENT,
  type HostTrpcClient,
} from "@flind/host-router/client";
import {
  DISK_CACHE_IMAGES,
  type IDiskCacheImages,
} from "@flind/platform/disk-cache";
import {
  FEEDBACK_CONTEXT_SERVICE,
  type IFeedbackContext,
} from "@flind/platform/feedback-context";
import {
  HOST_CAPABILITIES,
  type HostCapabilities,
} from "@flind/platform/host-capabilities";
import {
  type INotifications,
  NOTIFICATIONS_SERVICE,
} from "@flind/platform/notifications";
import type {
  IScreenCapture,
  SCREEN_CAPTURE_SERVICE,
} from "@flind/platform/screen-capture";
import type {
  ISettingsBackupFiles,
  SETTINGS_BACKUP_FILES,
} from "@flind/platform/settings-backup-files";
import { type ISpeech, SPEECH_SERVICE } from "@flind/platform/speech";
import {
  AUTH_SIDE_EFFECTS,
  type IAuthSideEffects,
} from "@flind/ui/features/auth/identifiers";
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
import type { FocusStoreCoordinator } from "@flind/ui/features/external-apps/focusCoordinator";
import {
  FEATURE_FLAGS,
  type FeatureFlags,
} from "@flind/ui/features/feature-flags/identifiers";
import {
  FILE_WATCHER_CLIENT,
  type FileWatcherClient,
} from "@flind/ui/features/file-watcher/identifiers";
import {
  FOCUS_CONTROLLER_DEPS,
  type FocusControllerDeps,
} from "@flind/ui/features/focus/focusClient";
import {
  GIT_CACHE_KEY_PROVIDER,
  type GitCacheKeyProvider,
} from "@flind/ui/features/git-interaction/gitCacheProvider";
import {
  MCP_APP_HOST_COMPONENT,
  MCP_SANDBOX_PROXY_URL,
  type McpAppHostComponent,
  type McpSandboxProxyUrlProvider,
} from "@flind/ui/features/mcp-apps/identifiers";
import {
  MISSION_CONTROL_CLIENT,
  type MissionControlClient,
} from "@flind/ui/features/mission-control/identifiers";
import {
  NAVIGATION_TASK_BINDER,
  type NavigationTaskBinder,
} from "@flind/ui/features/navigation/taskBinder";
import {
  ACTIVE_VIEW_PROVIDER,
  type IActiveView,
  type INotificationSettings,
  type ISpeechNotifySettings,
  NOTIFICATION_SETTINGS_PROVIDER,
  SPEECH_NOTIFY_SETTINGS,
} from "@flind/ui/features/notifications/identifiers";
import {
  AGENT_PROMPT_SENDER,
  type AgentPromptSender,
} from "@flind/ui/features/sessions/agentPromptSender";
import {
  ARTIFACT_HTML_FRAME_COMPONENT,
  type ArtifactHtmlFrameComponent,
} from "@flind/ui/features/sessions/components/artifactHtmlFrameHost";
import {
  MCP_TOOL_BLOCK_COMPONENT,
  type McpToolBlockComponent,
} from "@flind/ui/features/sessions/components/session-update/identifiers";
import {
  CLAUDE_SUBSCRIPTION_TOKEN_SETTINGS,
  type ClaudeSubscriptionTokenSettings,
} from "@flind/ui/features/settings/claudeSubscriptionTokenSettings";
import {
  DEV_MODE_CLIENT,
  type DevModeClient,
} from "@flind/ui/features/settings/devModeClient";
import {
  type ISpeechKeyStore,
  SPEECH_KEY_STORE,
} from "@flind/ui/features/settings/speechKeyStore";
import {
  SHELL_CLIENT,
  type ShellClient,
} from "@flind/ui/features/terminal/shellClient";
import {
  UPDATES_CLIENT,
  type UpdatesClient,
} from "@flind/ui/features/updates/updatesClient";
import {
  ANALYTICS_TRACKER,
  type AnalyticsTracker,
} from "@flind/ui/shell/analytics";
import {
  DIFF_WORKER_FACTORY,
  type DiffWorkerFactory,
} from "@flind/ui/shell/diffWorkerHost";
import {
  HEDGEHOG_MODE_HOST,
  type HedgehogModeHost,
} from "@flind/ui/shell/hedgehogModeHost";
import { HOST_LOGGER, type HostLogger } from "@flind/ui/shell/logger";
import {
  IMPERATIVE_QUERY_CLIENT,
  type ImperativeQueryClient,
} from "@flind/ui/shell/queryClient";
import {
  FILE_PATH_RESOLVER,
  type FilePathResolver,
} from "@flind/ui/utils/getFilePath";
import type { TRPCClient } from "@trpc/client";
import { TASK_SERVICE as RENDERER_TASK_SERVICE, TRPC_CLIENT } from "./tokens";

/**
 * Strongly-typed binding map for the renderer composition-root container.
 *
 * Covers every token directly bound on the renderer `container` across
 * `di/container.ts`, `desktop-services.ts`, and
 * `desktop-contributions.ts`. Tokens resolved purely through plain
 * `container.load(module)` are not listed here (TypedContainer accepts plain
 * ContainerModules without typing their internal bindings).
 */
export interface RendererBindings {
  [CODEX_CLOUD_ACCOUNT_HOST]: CodexCloudAccountHost;
  [SETTINGS_BACKUP_FILES]: ISettingsBackupFiles;
  // --- di/container.ts ---
  [HOST_LOGGER]: HostLogger;
  [TRPC_CLIENT]: TRPCClient<TrpcRouter>;
  [HOST_TRPC_CLIENT]: HostTrpcClient;
  [FEEDBACK_CONTEXT_SERVICE]: IFeedbackContext;
  [SCREEN_CAPTURE_SERVICE]: IScreenCapture;
  [UPDATES_CLIENT]: UpdatesClient;
  [DEV_MODE_CLIENT]: DevModeClient;
  [CONNECTIVITY_CLIENT]: ConnectivityClient;
  [BROWSER_TABS_CLIENT]: BrowserTabsClient;
  [DISCORD_PRESENCE_CLIENT]: DiscordPresenceClient;
  [MISSION_CONTROL_CLIENT]: MissionControlClient;
  [SHELL_CLIENT]: ShellClient;
  [FOCUS_CONTROLLER_DEPS]: FocusControllerDeps;
  [DIFF_WORKER_FACTORY]: DiffWorkerFactory;
  [REVIEW_HOST]: ReviewHost;
  [ARTIFACT_HTML_FRAME_COMPONENT]: ArtifactHtmlFrameComponent;
  [MCP_TOOL_BLOCK_COMPONENT]: McpToolBlockComponent;
  [MCP_APP_HOST_COMPONENT]: McpAppHostComponent;
  [MCP_SANDBOX_PROXY_URL]: McpSandboxProxyUrlProvider;
  [SHELL_PROCESS_READER]: ShellProcessReader;
  [ANALYTICS_TRACKER]: AnalyticsTracker;
  [TASK_CREATION_HOST]: ITaskCreationHost;
  [PI_RUNNER]: PiRunner;
  [PI_SESSION_PROVIDER]: PiSessionProvider;
  [LOCAL_PI_SESSION_FACTORY]: PiSessionFactory;
  [CLOUD_TASK_CLIENT]: CloudTaskClient;
  [TASK_CREATION_EFFECTS]: TaskCreationEffects;
  [RENDERER_TASK_SERVICE]: TaskService;
  [TASK_SERVICE]: TaskService;
  [WORKSPACE_SETUP_SAGA]: WorkspaceSetupSaga;
  [SESSION_SERVICE]: SessionService;
  [GIT_WRITE_CLIENT]: IGitWriteClient;
  [GIT_INTERACTION_EFFECTS]: GitInteractionEffects;
  [GIT_INTERACTION_SERVICE]: GitInteractionService;
  [TASK_DELETION_WORKSPACE_CLIENT]: ITaskDeletionWorkspaceClient;
  [TASK_DELETION_HOST]: ITaskDeletionHost;
  [TASK_DELETION_SERVICE]: TaskDeletionService;
  [EXTERNAL_APPS_WORKSPACE_CLIENT]: ExternalAppsWorkspaceClient;
  [EXTERNAL_APPS_FOCUS_COORDINATOR]: FocusStoreCoordinator;
  [EXTERNAL_APPS_SERVICE]: ExternalAppService;
  [WORKSPACE_SETUP_GIT_CLIENT]: WorkspaceSetupGitClient;
  [WORKSPACE_SETUP_SERVICE]: WorkspaceSetupService;
  [GITHUB_ISSUE_CLIENT]: GitHubIssueClient;
  [NEW_TASK_LINK_RESOLVER]: NewTaskLinkResolver;
  [CODE_REVIEW_WORKSPACE_CLIENT]: CodeReviewWorkspaceClient;
  [REVERT_HUNK_SERVICE]: RevertHunkService;
  [SKILLS_WORKSPACE_CLIENT]: SkillsWorkspaceClient;
  [LOCAL_MCP_WORKSPACE_CLIENT]: LocalMcpWorkspaceClient;
  [LOCAL_MCP_IMPORT_SERVICE]: LocalMcpImportService;
  [CLOUD_ARTIFACT_BUNDLE_LOCAL_SKILL]: BundleLocalSkill;
  [CLOUD_ARTIFACT_RESOLVE_SKILL_DEPENDENCIES]: ResolveSkillBundleDependencies;
  [CLOUD_ARTIFACT_READ_FILE_AS_BASE64]: ReadFileAsBase64;
  [LLM_GATEWAY_SERVICE]: LlmGatewayService;
  [FILE_READ_CLIENT]: FileReadClient;
  [TITLE_GENERATOR_GITHUB_PR_TITLE_CLIENT]: GithubPrTitleClient;
  [TITLE_GENERATOR_LOGGER]: TitleGeneratorLogger;

  // --- desktop-services.ts ---
  [IMPERATIVE_QUERY_CLIENT]: ImperativeQueryClient;
  [GIT_CACHE_KEY_PROVIDER]: GitCacheKeyProvider;
  [ARCHIVE_CLIENT]: ArchiveClient;
  [REPORT_MODEL_RESOLVER]: ReportModelResolver;
  [LINEAR_OAUTH_FLOW]: LinearOAuthFlow;
  [GITHUB_CONNECT_CLIENT]: GithubConnectClient;
  [INTEGRATIONS_GITHUB_CONNECT_CLIENT]: IntegrationsGithubConnectClient;
  [REPOSITORIES_CLIENT]: RepositoriesClient;
  [REPOSITORIES_SERVICE]: RepositoriesService;
  [HEDGEHOG_MODE_HOST]: HedgehogModeHost;
  [AGENT_PROMPT_SENDER]: AgentPromptSender;
  [AUTORESEARCH_SESSION_CLIENT]: AutoresearchSessionClient;
  [AUTORESEARCH_STORAGE_CLIENT]: AutoresearchStorageClient;
  [AUTORESEARCH_GATE]: AutoresearchGate;
  [FILE_PATH_RESOLVER]: FilePathResolver;
  [NAVIGATION_TASK_BINDER]: NavigationTaskBinder;
  [ROOT_LOGGER]: RootLogger;
  [NOTIFICATIONS_SERVICE]: INotifications;
  [NOTIFICATION_SETTINGS_PROVIDER]: INotificationSettings;
  [ACTIVE_VIEW_PROVIDER]: IActiveView;
  [SPEECH_SERVICE]: ISpeech;
  [SPEECH_SETTINGS_PROVIDER]: SpeechSettingsProvider;
  [SPEECH_USER_NAME_PROVIDER]: UserNameProvider;
  [SPEECH_NOTIFY_SETTINGS]: ISpeechNotifySettings;
  [SPEECH_KEY_STORE]: ISpeechKeyStore;
  [CLAUDE_SUBSCRIPTION_TOKEN_SETTINGS]: ClaudeSubscriptionTokenSettings;
  [FILE_WATCHER_CLIENT]: FileWatcherClient;
  [FEATURE_FLAGS]: FeatureFlags;
  [AUTH_SIDE_EFFECTS]: IAuthSideEffects;
  [SETUP_STORE]: ISetupStore;
  [HOST_CAPABILITIES]: HostCapabilities;
  [DISK_CACHE_IMAGES]: IDiskCacheImages;

  // --- desktop-contributions.ts ---
  [CONTRIBUTION]: Contribution;
  [AUTORESEARCH_SERVICE]: AutoresearchService;
}
