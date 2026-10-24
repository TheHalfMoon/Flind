import { SETUP_RUN_SERVICE } from "@flind/core/setup/identifiers";
import { ContainerModule } from "inversify";
import { SetupRunServiceImpl } from "./setupRunServiceImpl";

export const setupUiModule = new ContainerModule(({ bind }) => {
  bind(SETUP_RUN_SERVICE).to(SetupRunServiceImpl).inSingletonScope();
});
