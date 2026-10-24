import { CONTRIBUTION } from "@flind/di/contribution";
import { ContainerModule } from "inversify";
import { DiscordPresenceContribution } from "./discordPresence.contribution";

export const discordPresenceUiModule = new ContainerModule(({ bind }) => {
  bind(CONTRIBUTION).to(DiscordPresenceContribution).inSingletonScope();
});
