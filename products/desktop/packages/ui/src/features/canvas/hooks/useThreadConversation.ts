import {
  buildThreadTimeline,
  deriveThreadAgentStatus,
  hasAgentMention,
  shouldSuspendThreadSession,
  type ThreadAgentStatus,
  type ThreadTimelineRow,
} from "@flind/core/canvas/threadTimeline";
import { ANALYTICS_EVENTS } from "@flind/shared/analytics-events";
import type {
  Task,
  TaskThreadMessage,
  UserBasic,
} from "@flind/shared/domain-types";
import { isTerminalStatus } from "@flind/shared/domain-types";
import { useOptionalAuthenticatedClient } from "@flind/ui/features/auth/authClient";
import { useCurrentUser } from "@flind/ui/features/auth/useCurrentUser";
import { useOrgMembers } from "@flind/ui/features/canvas/hooks/useOrgMembers";
import {
  useDeleteTaskThreadMessage,
  usePostTaskThreadMessage,
  usePostTaskThreadMessageToAgent,
  useSendTaskThreadMessageToAgent,
  useTaskThread,
} from "@flind/ui/features/canvas/hooks/useTaskThread";
import { useSessionConnection } from "@flind/ui/features/sessions/hooks/useSessionConnection";
import { useSessionViewState } from "@flind/ui/features/sessions/hooks/useSessionViewState";
import { usePendingPermissionsForTask } from "@flind/ui/features/sessions/sessionStore";
import { toast } from "@flind/ui/primitives/toast";
import { track } from "@flind/ui/shell/analytics";
import { useCallback, useMemo, useState } from "react";

export type ThreadSurface = "thread_panel" | "activity_panel";

type SessionEvents = ReturnType<typeof useSessionViewState>["events"];

export interface ThreadConversation {
  timeline: ThreadTimelineRow<TaskThreadMessage>[];
  /** Every thread message, unfiltered. `timeline` is the human-facing subset, so a surface
   *  that draws agent and system rows has to start here instead. */
  messages: TaskThreadMessage[];
  agentStatus: ThreadAgentStatus | null;
  events: SessionEvents;
  isPromptPending: boolean;
  /** The thread's own durable content has arrived. Unlike the live session's
   *  connect state, this never goes back to false once true. */
  hasLoadedThread: boolean;
  members: UserBasic[];
  currentUser: { id?: number; uuid?: string; email?: string } | undefined;
  isTaskAuthor: boolean;
  canForward: boolean;
  draft: string;
  setDraft: (value: string) => void;
  isSubmitDisabled: boolean;
  submit: () => Promise<void>;
  sendMessageToAgent: (messageId: string) => void;
  deleteMessage: (messageId: string) => void;
  onMentionInsert: (member: UserBasic) => void;
}

export function useThreadConversation(
  task: Task,
  { surface }: { surface: ThreadSurface },
): ThreadConversation {
  const taskId = task.id;
  const client = useOptionalAuthenticatedClient();
  const { data: currentUser } = useCurrentUser({ client });

  const { messages, hasLoaded: hasLoadedThread } = useTaskThread(taskId);
  const { postMessage, isPosting } = usePostTaskThreadMessage(taskId);
  const { postMessageToAgent, isPostingToAgent } =
    usePostTaskThreadMessageToAgent(taskId);
  const { deleteMessage } = useDeleteTaskThreadMessage(taskId);
  const { sendToAgent, isSending } = useSendTaskThreadMessageToAgent(taskId);
  const isSendingToAgent = isPostingToAgent || isSending;
  const { members } = useOrgMembers();

  const {
    session,
    repoPath,
    isCloud,
    events,
    cloudStatus,
    isPromptPending,
    isInitializing,
    hasError,
    errorTitle,
  } = useSessionViewState(taskId, task);
  useSessionConnection({
    taskId,
    task,
    session,
    repoPath,
    isCloud,
    isSuspended: shouldSuspendThreadSession({
      isCloud,
      hasRun: Boolean(task.latest_run?.id),
      hasSession: Boolean(session),
    }),
  });
  const pendingPermissions = usePendingPermissionsForTask(taskId);

  const agentStatus = useMemo(
    () =>
      deriveThreadAgentStatus({
        hasActivity: events.length > 0 || !!task.latest_run,
        hasError,
        cloudStatus,
        errorTitle,
        pendingPermissionCount: pendingPermissions.size,
        isPromptPending,
        isInitializing,
      }),
    [
      events.length,
      task.latest_run,
      hasError,
      cloudStatus,
      errorTitle,
      pendingPermissions.size,
      isPromptPending,
      isInitializing,
    ],
  );

  const timeline = useMemo(() => buildThreadTimeline(messages), [messages]);

  const [draft, setDraft] = useState("");

  const onMentionInsert = useCallback(
    (member: UserBasic) => {
      track(ANALYTICS_EVENTS.CHANNEL_ACTION, {
        action_type: "mention_member",
        surface,
        task_id: taskId,
        mentioned_user_id: member.uuid,
      });
    },
    [taskId, surface],
  );

  const isTaskAuthor =
    !!currentUser?.uuid && currentUser.uuid === task.created_by?.uuid;
  const canForward =
    !!task.latest_run &&
    !isTerminalStatus(task.latest_run.status) &&
    !isSendingToAgent;

  const submit = async () => {
    const content = draft.trim();
    if (!content || isPosting || isSendingToAgent) return;
    const sendToAgentRequested = hasAgentMention(content);
    if (sendToAgentRequested && (!isTaskAuthor || !canForward)) {
      toast.error("Couldn't send to agent", {
        description:
          "Only the task author can @agent while the task has an active run.",
      });
      return;
    }
    setDraft("");
    try {
      if (sendToAgentRequested) {
        const { sendError } = await postMessageToAgent(content);
        if (sendError) {
          toast.error("Message posted, but couldn't send it to the agent", {
            description:
              sendError instanceof Error
                ? sendError.message
                : String(sendError),
          });
        }
      } else {
        await postMessage(content);
      }
    } catch (error) {
      // Hand the draft back rather than losing what they typed.
      setDraft(content);
      toast.error("Couldn't post message", {
        description: error instanceof Error ? error.message : String(error),
      });
    }
  };

  const sendMessageToAgent = (messageId: string) => {
    sendToAgent(messageId).catch((error: unknown) => {
      toast.error("Couldn't send message to agent", {
        description: error instanceof Error ? error.message : String(error),
      });
    });
  };

  const handleDelete = (messageId: string) => {
    deleteMessage(messageId).catch((error: unknown) => {
      toast.error("Couldn't delete message", {
        description: error instanceof Error ? error.message : String(error),
      });
    });
  };

  return {
    timeline,
    messages,
    agentStatus,
    events,
    isPromptPending,
    hasLoadedThread,
    members,
    currentUser,
    isTaskAuthor,
    canForward,
    draft,
    setDraft,
    isSubmitDisabled: !draft.trim() || isPosting || isSendingToAgent,
    submit,
    sendMessageToAgent,
    deleteMessage: handleDelete,
    onMentionInsert,
  };
}
