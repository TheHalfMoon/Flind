import { CONTRIBUTION } from "@flind/di/contribution";
import { ContainerModule } from "inversify";
import { BillingContribution } from "./billing.contribution";

export const billingUiModule = new ContainerModule(({ bind }) => {
  bind(CONTRIBUTION).to(BillingContribution).inSingletonScope();
});
