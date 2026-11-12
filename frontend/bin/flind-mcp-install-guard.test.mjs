import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const read = (path) => readFileSync(new URL(path, import.meta.url), 'utf8')

test('Flind does not advertise an unverified external MCP installer', () => {
    const constants = read('../src/lib/components/MCPHint/constants.ts')
    assert.match(constants, /FLIND_MCP_INSTALL_AVAILABLE:\s*boolean\s*=\s*false/)
    assert.match(constants, /MCP_INSTALL_COMMAND\s*=\s*''/)
    assert.doesNotMatch(constants, /@posthog\/wizard/)
    const setup = read('../src/scenes/settings/environment/MCPServerSettings.tsx')
    assert.doesNotMatch(setup, /@posthog\/wizard|posthog\.com\/docs/)
    assert.match(setup, /does not yet provide a verified MCP installation command/)
})

test('all MCP installer promotion surfaces are gated', () => {
    const surfaces = [
        '../src/lib/components/MCPHint/MCPHintActions.tsx',
        '../src/lib/components/NavPanelAdvertisement/NavPanelMcpCard.tsx',
        '../src/lib/components/AgentPromptButton/AgentPromptButton.tsx',
        '../../products/ai_observability/frontend/evaluations/components/EvaluationAgentActions.tsx',
    ]
    for (const path of surfaces) {
        assert.match(read(path), /FLIND_MCP_INSTALL_AVAILABLE/, path)
    }
    assert.match(
        read('../src/lib/components/AgentPromptButton/AgentPromptButton.tsx'),
        /\|\| !FLIND_MCP_INSTALL_AVAILABLE/
    )
})
