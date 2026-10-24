import type { McpUiResourceCsp } from "@modelcontextprotocol/ext-apps/app-bridge";

export interface McpUiResource {
  uri: string;
  html: string;
  csp?: McpUiResourceCsp;
  permissions?: Record<string, Record<string, unknown>>;
}
