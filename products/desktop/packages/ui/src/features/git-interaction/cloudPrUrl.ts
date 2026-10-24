import { mergePrUrls, readPrSummaries, readPrUrls } from "@flind/shared";
import type { Task } from "@flind/shared/domain-types";
import type { AgentSession } from "@flind/ui/features/sessions/sessionStore";

export function resolveCloudPrUrls(
  task: Task | undefined,
  session: Pick<AgentSession, "cloudOutput"> | undefined,
): string[] {
  return mergePrUrls(
    readPrUrls(task?.latest_run?.output),
    readPrUrls(session?.cloudOutput),
  );
}

export function resolveCloudPrSummaries(
  task: Task | undefined,
  session: Pick<AgentSession, "cloudOutput"> | undefined,
): Record<string, string> {
  return {
    ...readPrSummaries(session?.cloudOutput),
    ...readPrSummaries(task?.latest_run?.output),
  };
}

export function resolveCloudPrUrl(
  task: Task | undefined,
  session: Pick<AgentSession, "cloudOutput"> | undefined,
): string | null {
  return resolveCloudPrUrls(task, session)[0] ?? null;
}
