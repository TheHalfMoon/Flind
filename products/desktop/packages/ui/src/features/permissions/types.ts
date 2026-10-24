import type {
  PermissionOption,
  RequestPermissionRequest,
  ToolCallContent,
} from "@agentclientprotocol/sdk";
import { getPermissionOptionMeta } from "@flind/core/sessions/permissionResponse";
import type { CodeToolKind } from "@flind/ui/features/sessions/types";
import type { SelectorOption } from "@flind/ui/primitives/ActionSelector";

type AcpToolCall = RequestPermissionRequest["toolCall"];
export type PermissionToolCall = Omit<AcpToolCall, "kind"> & {
  kind?: CodeToolKind | null;
};

export interface BasePermissionProps {
  toolCall: PermissionToolCall;
  options: PermissionOption[];
  onSelect: (
    optionId: string,
    customInput?: string,
    answers?: Record<string, string>,
  ) => void;
  onCancel: () => void;
}

export function toSelectorOptions(
  options: PermissionOption[],
): SelectorOption[] {
  return options.map((opt) => {
    const meta = getPermissionOptionMeta(opt);
    return {
      id: opt.optionId,
      label: opt.name,
      description: meta.description,
      customInput: meta.customInput,
    };
  });
}

export { findDiffContent } from "@flind/ui/features/sessions/components/session-update/toolCallUtils";
export type StandardContent = Extract<ToolCallContent, { type: "content" }>;

export function findTextContent(
  content: ToolCallContent[] | null | undefined,
): string | undefined {
  const stdContent = content?.find(
    (c): c is StandardContent => c.type === "content",
  );
  if (stdContent?.content.type === "text") {
    return stdContent.content.text;
  }
  return undefined;
}
