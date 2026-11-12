// Flind has not shipped a qualified instance-specific MCP installer.
// Keep the previous setup widgets disabled until an actual Flind installer replaces
// the donor CLI; existing manually configured MCP connections are unaffected.
export const FLIND_MCP_INSTALL_AVAILABLE: boolean = false

// No inherited provider CLI is safe to copy from Flind; populate only after the Flind installer is built and tested.
export const MCP_INSTALL_COMMAND = ''
