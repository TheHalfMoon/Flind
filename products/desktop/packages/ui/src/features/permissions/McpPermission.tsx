import {
  formatPosthogExecBody,
  getPostHogExecDisplay,
  isPostHogExecTool,
} from "@flind/core/sessions/posthogExecDisplay";
import { mcpToolKey, readMcpToolDescriptor } from "@flind/shared";
import { formatInput } from "@flind/ui/features/sessions/components/session-update/toolCallUtils";
import { ActionSelector } from "@flind/ui/primitives/ActionSelector";
import { Box, Code } from "@radix-ui/themes";
import { DefaultPermission } from "./DefaultPermission";
import { type BasePermissionProps, toSelectorOptions } from "./types";

export function McpPermission({
  toolCall,
  options,
  onSelect,
  onCancel,
}: BasePermissionProps) {
  const mcp = readMcpToolDescriptor(toolCall._meta);

  if (!mcp) {
    return (
      <DefaultPermission
        toolCall={toolCall}
        options={options}
        onSelect={onSelect}
        onCancel={onCancel}
      />
    );
  }

  const posthogDisplay = isPostHogExecTool(mcpToolKey(mcp))
    ? getPostHogExecDisplay(toolCall.rawInput)
    : null;
  const serverName = posthogDisplay ? "posthog" : mcp.server;
  const toolName = posthogDisplay?.label ?? mcp.tool;
  const fullInput = posthogDisplay
    ? formatPosthogExecBody(posthogDisplay.input)
    : formatInput(toolCall.rawInput);

  return (
    <ActionSelector
      title={
        <>
          <span className="text-gray-10">{serverName}</span>
          {" - "}
          {toolName}
          <span className="text-gray-10">{" (MCP)"}</span>
        </>
      }
      pendingAction={
        fullInput ? (
          <Box className="max-h-[30vh] overflow-auto">
            <Code
              variant="ghost"
              className="whitespace-pre-wrap break-all text-[13px]"
            >
              {fullInput}
            </Code>
          </Box>
        ) : undefined
      }
      question="Do you want to proceed?"
      options={toSelectorOptions(options)}
      onSelect={onSelect}
      onCancel={onCancel}
    />
  );
}
