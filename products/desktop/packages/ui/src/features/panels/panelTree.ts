import * as core from "@flind/core/panels/panelTree";
import type { PanelNode, Tab } from "./panelTypes";

export const findTabInTree = core.findTabInTree as (
  node: PanelNode,
  tabId: string,
) => { panelId: string; tab: Tab } | null;
