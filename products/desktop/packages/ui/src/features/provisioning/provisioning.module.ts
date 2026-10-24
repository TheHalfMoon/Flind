import { CONTRIBUTION } from "@flind/di/contribution";
import { ContainerModule } from "inversify";
import { ProvisioningContribution } from "./provisioning.contribution";

export const provisioningUiModule = new ContainerModule(({ bind }) => {
  bind(CONTRIBUTION).to(ProvisioningContribution).inSingletonScope();
});
