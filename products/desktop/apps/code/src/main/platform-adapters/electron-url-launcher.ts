import type { IUrlLauncher } from "@flind/platform/url-launcher";
import { shell } from "electron";
import { injectable } from "inversify";

@injectable()
export class ElectronUrlLauncher implements IUrlLauncher {
  public async launch(url: string): Promise<void> {
    await shell.openExternal(url);
  }
}
