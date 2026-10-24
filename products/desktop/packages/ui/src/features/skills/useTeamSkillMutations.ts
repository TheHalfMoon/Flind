import { TEAM_SKILLS_SERVICE } from "@flind/core/skills/identifiers";
import type { TeamSkillsService } from "@flind/core/skills/teamSkillsService";
import { useService } from "@flind/di/react";
import { useHostTRPC } from "@flind/host-router/react";
import { useAuthenticatedMutation } from "@flind/ui/hooks/useAuthenticatedMutation";
import { useQueryClient } from "@tanstack/react-query";
import { teamSkillsKeys } from "./useTeamSkills";

/** Publishes a local user/repo skill to the team as a new LLMSkill version. */
export function usePublishSkill() {
  const service = useService<TeamSkillsService>(TEAM_SKILLS_SERVICE);
  const queryClient = useQueryClient();
  return useAuthenticatedMutation(
    (client, variables: { skillPath: string }) =>
      service.publishLocalSkill(client, variables.skillPath),
    {
      onSuccess: () => {
        void queryClient.invalidateQueries({ queryKey: teamSkillsKeys.all });
      },
    },
  );
}

/** Materializes a team skill into ~/.claude/skills (copy-and-forget). */
export function useInstallTeamSkill() {
  const service = useService<TeamSkillsService>(TEAM_SKILLS_SERVICE);
  const trpc = useHostTRPC();
  const queryClient = useQueryClient();
  return useAuthenticatedMutation(
    (client, variables: { name: string; overwrite?: boolean }) =>
      service.installTeamSkillLocally(
        client,
        variables.name,
        variables.overwrite ?? false,
      ),
    {
      onSuccess: () => {
        void queryClient.invalidateQueries(trpc.skills.pathFilter());
        void queryClient.invalidateQueries({ queryKey: teamSkillsKeys.all });
      },
    },
  );
}
