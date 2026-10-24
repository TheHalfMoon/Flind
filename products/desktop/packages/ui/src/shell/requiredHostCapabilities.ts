import { REPORT_MODEL_RESOLVER } from "@flind/core/inbox/identifiers";
import {
  SPEECH_SETTINGS_PROVIDER,
  SPEECH_USER_NAME_PROVIDER,
} from "@flind/core/speech/identifiers";
import type { HostCapabilityRequirement } from "@flind/di/hostCapabilities";
import { FEEDBACK_CONTEXT_SERVICE } from "@flind/platform/feedback-context";
import { HOST_CAPABILITIES } from "@flind/platform/host-capabilities";
import { SPEECH_SERVICE } from "@flind/platform/speech";
import { AUTH_SIDE_EFFECTS } from "@flind/ui/features/auth/identifiers";
import { REVIEW_HOST } from "@flind/ui/features/code-review/reviewHost";
import { CONNECTIVITY_CLIENT } from "@flind/ui/features/connectivity/connectivityClient";
import { FEATURE_FLAGS } from "@flind/ui/features/feature-flags/identifiers";
import { GIT_CACHE_KEY_PROVIDER } from "@flind/ui/features/git-interaction/gitCacheProvider";
import { SPEECH_NOTIFY_SETTINGS } from "@flind/ui/features/notifications/identifiers";
import { AGENT_PROMPT_SENDER } from "@flind/ui/features/sessions/agentPromptSender";
import { UPDATES_CLIENT } from "@flind/ui/features/updates/updatesClient";
import { DIFF_WORKER_FACTORY } from "@flind/ui/shell/diffWorkerHost";

/**
 * Host capabilities every host mounting the shared app must bind.
 *
 * The contract: shared `@flind/ui` / `@flind/core` resolve these tokens via
 * `useService` / `resolveService`, so any host that renders the shared UI has to
 * provide an implementation. Unlike a `TypedContainer<HostBindings>` (which only
 * type-checks the provider side) or a tRPC procedure stub (which may legitimately
 * `NOT_FOUND` at call time), a missing binding here is always a bug — it just
 * hides until a user reaches the resolving code path.
 *
 * Each host passes this list to `assertHostCapabilities` at the end of its
 * composition root (see `apps/web/src/web-container.ts` and the desktop renderer
 * container) so a gap fails at startup rather than at the first navigation that
 * needs it — which the web e2e boot test (`apps/web/tests/e2e`) turns into a CI
 * gate: an unbound capability throws at container load, the app never mounts,
 * and the boot spec fails. Add an entry whenever shared code starts resolving a
 * new host-provided token via service location.
 *
 * Excluded on purpose: core-module services (they fail at module load, a
 * different and already-loud failure mode) and host-specific/local-only
 * capabilities such as file watchers that not every host provides.
 */
export const REQUIRED_HOST_CAPABILITIES: readonly HostCapabilityRequirement[] =
  [
    {
      token: HOST_CAPABILITIES,
      description: "coarse host capability flags the shared UI branches on",
    },
    {
      token: FEATURE_FLAGS,
      description: "feature-flag gating across the app",
    },
    {
      token: FEEDBACK_CONTEXT_SERVICE,
      description: "recent app logs for explicit feedback attachments",
    },
    {
      token: AUTH_SIDE_EFFECTS,
      description: "auth lifecycle side effects (login/logout/session)",
    },
    {
      token: CONNECTIVITY_CLIENT,
      description: "online/offline status the UI reacts to",
    },
    {
      token: UPDATES_CLIENT,
      description: "app-update status surfaced in settings",
    },
    {
      token: GIT_CACHE_KEY_PROVIDER,
      description: "git query cache keys",
    },
    {
      token: REVIEW_HOST,
      description: "code-review page host wiring",
    },
    {
      token: AGENT_PROMPT_SENDER,
      description:
        "send-a-prompt-to-the-agent actions (sendPromptToAgent, edit flag in task)",
    },
    {
      token: DIFF_WORKER_FACTORY,
      description: "diff computation worker for review/diffs",
    },
    {
      token: REPORT_MODEL_RESOLVER,
      description: "default cloud-run model resolution (canvas/home/inbox)",
    },
    {
      token: SPEECH_SERVICE,
      description: "text-to-speech playback for agent narration",
    },
    {
      token: SPEECH_SETTINGS_PROVIDER,
      description: "spoken-narration enablement and voice",
    },
    {
      token: SPEECH_USER_NAME_PROVIDER,
      description: "signed-in user's first name for spoken greetings",
    },
    {
      token: SPEECH_NOTIFY_SETTINGS,
      description: "per-kind gating for spoken notifications",
    },
  ];
