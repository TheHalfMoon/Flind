import type { WorkspaceClient } from "@flind/workspace-client/client";

export const ENVIRONMENT_CLIENT = Symbol.for("posthog.host.environmentClient");

export interface HostEnvironmentClient {
  environment: WorkspaceClient["environment"];
}
