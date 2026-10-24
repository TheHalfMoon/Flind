export function isMcpOAuthRedirect(
  response: object,
): response is { redirect_url: string } {
  return (
    "redirect_url" in response && typeof response.redirect_url === "string"
  );
}

/**
 * The generated MCP server DTO omits this optional compatibility field, while
 * some self-hosted instances include it. Accept the DTO without casting it
 * to a structurally incompatible type and check the optional runtime field.
 */
export function isStdioMcpServer(server: unknown): boolean {
  return (
    typeof server === "object" &&
    server !== null &&
    "transport_type" in server &&
    server.transport_type === "stdio"
  );
}
