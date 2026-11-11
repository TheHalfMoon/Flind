import { SparkleIcon } from "@phosphor-icons/react";
import { prettifyScoutSkillName } from "@flind/core/scouts/scoutPresentation";
import { buildScoutCheckinPrompt } from "@flind/core/scouts/scoutPrompts";
import { Button } from "@flind/quill";
import type { ScoutSurface } from "@flind/shared";
import { Tooltip } from "@flind/ui/primitives/Tooltip";
import { useMemo } from "react";
import { useScoutChatTask } from "../hooks/useScoutChatTask";

/**
 * One-click check-in on a scout: creates an auto-mode cloud task that asks
 * Flind about this scout and opens it. Icon-only unless a label is given.
 */
export function ScoutChatButton({
  skillName,
  surface,
  label,
}: {
  skillName: string;
  surface: ScoutSurface;
  label?: string;
}) {
  const prompt = useMemo(
    () => buildScoutCheckinPrompt(skillName, prettifyScoutSkillName(skillName)),
    [skillName],
  );
  const { runTask, isRunning } = useScoutChatTask({
    prompt,
    taskLabel: "agent check-in",
    loggerScope: "scout-checkin",
    chatType: "scout_checkin",
    surface,
    skillName,
  });

  if (label) {
    return (
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={() => void runTask()}
        disabled={isRunning}
        data-attr="scout-discuss"
      >
        <SparkleIcon size={13} />
        {isRunning ? "Starting…" : label}
      </Button>
    );
  }

  return (
    <Tooltip content="Ask Flind about this agent">
      <Button
        type="button"
        variant="default"
        size="icon-sm"
        onClick={() => void runTask()}
        disabled={isRunning}
        aria-label={`Ask Flind about the ${skillName} agent`}
        className={isRunning ? "animate-pulse text-(--iris-9)" : undefined}
        data-attr="scout-discuss"
      >
        <SparkleIcon size={14} />
      </Button>
    </Tooltip>
  );
}
