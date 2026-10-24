import type { RpcExtensionUIResponse } from "@flind/agent/pi/types";
import type { PiExtensionDialogRequest } from "@flind/core/pi-runtime/piExtensionStore";

export function buildPiExtensionResponse(
  request: PiExtensionDialogRequest,
  value: string | boolean,
): RpcExtensionUIResponse {
  if (request.method === "confirm") {
    return {
      type: "extension_ui_response",
      id: request.id,
      confirmed: value === true,
    };
  }
  return {
    type: "extension_ui_response",
    id: request.id,
    value: typeof value === "string" ? value : "",
  };
}
