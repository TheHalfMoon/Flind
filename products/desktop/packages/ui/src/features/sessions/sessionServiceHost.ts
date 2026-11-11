import { DEFAULT_GATEWAY_MODEL } from "@flind/agent/gateway-models";
import { getIsOnline } from "@flind/core/connectivity/connectivityStore";
import {
  AGENT_SESSION_NOTIFIER,
  type AgentSessionNotifier,
} from "@flind/core/notification/agentSessionNotifications";
import { CloudArtifactService } from "@flind/core/sessions/cloudArtifactService";
import {
  combineQueuedCloudPrompts,
  getCloudPromptTransport,
} from "@flind/core/sessions/cloudPrompt";
import {
  SessionService,
  type SessionServiceDeps,
} from "@flind/core/sessions/sessionService";
import { extractSkillButtonId } from "@flind/core/skill-buttons/prompts";
import { resolveService } from "@flind/di/container";
import {
  HOST_TRPC_CLIENT,
  type HostTrpcClient,
} from "@flind/host-router/client";
import {
  BEDROCK_GATEWAY_VARIANTS,
  BEDROCK_LLM_GATEWAY_FLAG,
  type BedrockGatewayVariant,
  CLAUDE_OWN_SUBSCRIPTION_CLOUD_FLAG,
  CLAUDE_OWN_SUBSCRIPTION_FLAG,
  CODEX_OWN_SUBSCRIPTION_CLOUD_FLAG,
  CODEX_OWN_SUBSCRIPTION_FLAG,
  SPOKEN_NARRATION_FLAG,
} from "@flind/shared";
import {
  createAuthenticatedClient,
  getAuthenticatedClient,
} from "@flind/ui/features/auth/authClientImperative";
import { fetchAuthState } from "@flind/ui/features/auth/authQueries";
import { useUsageLimitStore } from "@flind/ui/features/billing/usageLimitStore";
import {
  FEATURE_FLAGS,
  type FeatureFlags,
} from "@flind/ui/features/feature-flags/identifiers";
import { useAddDirectoryDialogStore } from "@flind/ui/features/folder-picker/addDirectoryDialogStore";
import { SpeechNotifier } from "@flind/ui/features/notifications/speechNotifier";
import { useSessionAdapterStore } from "@flind/ui/features/sessions/sessionAdapterStore";
import {
  getPersistedConfigOptions,
  removePersistedConfigOptions,
  setPersistedConfigOptions,
} from "@flind/ui/features/sessions/sessionConfigStore";
import { sessionStoreSetters } from "@flind/ui/features/sessions/sessionStore";
import {
  getEffectiveCustomInstructions,
  useSettingsStore,
} from "@flind/ui/features/settings/settingsStore";
import { taskViewedApi } from "@flind/ui/features/sidebar/taskMetaApi";
import { WORKSPACE_QUERY_KEY } from "@flind/ui/features/workspace/identifiers";
import { toast } from "@flind/ui/primitives/toast";
import {
  buildPermissionToolMetadata,
  track,
} from "@flind/ui/shell/posthogAnalyticsImpl";
import { logger } from "../../shell/logger";
import {
  IMPERATIVE_QUERY_CLIENT,
  type ImperativeQueryClient,
} from "../../shell/queryClient";
import { resolveLocalSkillPrompt } from "../message-editor/commands";

export { SessionService };

const log = logger.scope("session-service");

export function shouldEnableSpokenNarration(
  userOptedIn: boolean,
  flagEnabled: boolean,
  isDevelopment: boolean,
): boolean {
  return userOptedIn && (flagEnabled || isDevelopment);
}

/**
 * Narrow the raw flag value to a known variant. An unmatched flag, an
 * unresolved one, or a variant added in Flind that this build does not know
 * about all yield undefined, which leaves the session on the gateway's default
 * provider rather than guessing.
 *
 * posthog-js resolves flags asynchronously, so a session started before the
 * first load finishes reads undefined and runs on Anthropic. That window is
 * effectively the first launch after install, because posthog-js restores
 * cached flags from its persistence layer on init, and this flag matches on
 * `email`, which only exists once `identify` runs.
 *
 * An unresolved variant is deliberately not treated as `control`: the session
 * sends no `$feature/` property at all, so it drops out of both arms instead of
 * inflating control. That keeps the comparison honest at the cost of losing a
 * few early sessions. Waiting for flags here would put a network round trip in
 * front of every session start and reconnect, which is a worse trade.
 */
function resolveBedrockGatewayVariant(
  rawVariant: string | undefined,
): BedrockGatewayVariant | undefined {
  return BEDROCK_GATEWAY_VARIANTS.find((variant) => variant === rawVariant);
}

function hostClient(): HostTrpcClient {
  return resolveService<HostTrpcClient>(HOST_TRPC_CLIENT);
}

function buildSessionServiceDeps(): SessionServiceDeps {
  const trpc = hostClient();
  const queryClient = resolveService<ImperativeQueryClient>(
    IMPERATIVE_QUERY_CLIENT,
  );
  const cloudArtifactService = new CloudArtifactService(
    (filePath) => trpc.fs.readFileAsBase64.query({ filePath }),
    (skillBundleRef) => trpc.skills.bundleLocal.query(skillBundleRef),
    (skillBundleRefs) => trpc.skills.resolveDependencies.query(skillBundleRefs),
  );

  return {
    trpc,
    store: sessionStoreSetters,
    log,
    toast: {
      error: (msg, opts) => toast.error(msg, opts),
      info: (msg, opts) => toast.info(msg, opts),
    },
    track: (event, props) => {
      (track as (event: string, props?: Record<string, unknown>) => void)(
        event,
        props,
      );
    },
    buildPermissionToolMetadata,
    notifyAgentSession: (notification) =>
      resolveService<AgentSessionNotifier>(AGENT_SESSION_NOTIFIER).notify(
        notification,
      ),
    enqueueSpeech: (request) => resolveService(SpeechNotifier).speak(request),
    getIsOnline,
    fetchAuthState,
    getAuthenticatedClient,
    createAuthenticatedClient,
    getPersistedConfigOptions: (taskRunId) =>
      getPersistedConfigOptions(taskRunId) ?? undefined,
    setPersistedConfigOptions,
    removePersistedConfigOptions,
    adapterStore: {
      getAdapter: (taskRunId) =>
        useSessionAdapterStore.getState().getAdapter(taskRunId),
      setAdapter: (taskRunId, adapter) =>
        useSessionAdapterStore.getState().setAdapter(taskRunId, adapter),
      removeAdapter: (taskRunId) =>
        useSessionAdapterStore.getState().removeAdapter(taskRunId),
    },
    get settings() {
      const state = useSettingsStore.getState();
      const featureFlags = resolveService<FeatureFlags>(FEATURE_FLAGS);
      const codexSubscriptionEnabled =
        featureFlags.isEnabled(CODEX_OWN_SUBSCRIPTION_FLAG) ||
        import.meta.env.DEV;
      const claudeSubscriptionEnabled =
        featureFlags.isEnabled(CLAUDE_OWN_SUBSCRIPTION_FLAG) ||
        import.meta.env.DEV;
      return {
        ...state,
        claudeCloudSubscriptionEnabled: featureFlags.isEnabled(
          CLAUDE_OWN_SUBSCRIPTION_CLOUD_FLAG,
        ),
        codexCloudSubscriptionEnabled: featureFlags.isEnabled(
          CODEX_OWN_SUBSCRIPTION_CLOUD_FLAG,
        ),
        customInstructions: getEffectiveCustomInstructions(state),
        spokenNarrationEnabled: shouldEnableSpokenNarration(
          state.spokenNotifications,
          featureFlags.isEnabled(SPOKEN_NARRATION_FLAG),
          import.meta.env.DEV,
        ),
        bedrockGatewayVariant: resolveBedrockGatewayVariant(
          featureFlags.getVariant(BEDROCK_LLM_GATEWAY_FLAG),
        ),
        codexModelAccess: codexSubscriptionEnabled
          ? state.codexModelAccess
          : undefined,
        claudeModelAccess: claudeSubscriptionEnabled
          ? state.claudeModelAccess
          : undefined,
      };
    },
    usageLimit: {
      show: (...args) => useUsageLimitStore.getState().show(...args),
    },
    get addDirectoryDialog() {
      return { open: useAddDirectoryDialogStore.getState().open };
    },
    taskViewedApi: {
      markActivity: (taskId) => taskViewedApi.markActivity(taskId),
    },
    queryClient,
    DEFAULT_GATEWAY_MODEL,
    WORKSPACE_QUERY_KEY,
    h: {
      extractSkillButtonId,
      combineQueuedCloudPrompts,
      getCloudPromptTransport,
      resolveLocalSkillCommandPrompt: (prompt) =>
        resolveLocalSkillPrompt(prompt, () => trpc.skills.list.query()),
      uploadRunOutput: (client, taskId, runId, name, content, contentType) =>
        cloudArtifactService.uploadRunOutput(
          client,
          taskId,
          runId,
          name,
          content,
          contentType,
        ),
      uploadRunAttachments: (client, taskId, runId, filePaths, skillBundles) =>
        cloudArtifactService.uploadRunAttachments(
          client,
          taskId,
          runId,
          filePaths,
          skillBundles,
        ),
      uploadTaskStagedAttachments: (client, taskId, filePaths, skillBundles) =>
        cloudArtifactService.uploadTaskStagedAttachments(
          client,
          taskId,
          filePaths,
          skillBundles,
        ),
    },
  };
}

// --- Singleton Service Instance ---

let serviceInstance: SessionService | null = null;

export function getSessionService(): SessionService {
  if (!serviceInstance) {
    serviceInstance = new SessionService(buildSessionServiceDeps());
  }
  return serviceInstance;
}

export function resetSessionService(): void {
  if (serviceInstance) {
    serviceInstance.reset();
    serviceInstance = null;
  }

  sessionStoreSetters.clearAll();

  hostClient()
    .agent.resetAll.mutate()
    .catch((err) => {
      log.error("Failed to reset all sessions on main process", err);
    });
}
