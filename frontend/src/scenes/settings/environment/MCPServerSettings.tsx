const MCPServerSettings = (): JSX.Element => {
    return (
        <div>
            <p className="pb-2">
                Flind does not yet provide a verified MCP installation command for this deployment.
            </p>
            <p>
                If your Flind administrator has configured an MCP server, use the connection details they provided.
                Do not run installation commands intended for another analytics service.
            </p>
        </div>
    )
}

export default MCPServerSettings
