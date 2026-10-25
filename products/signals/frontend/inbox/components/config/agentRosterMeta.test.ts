import { AGENT_ROSTER_GROUPS } from './agentRosterMeta'

describe('Flind signal roster first-party help', () => {
    it('uses Flind visible branding without changing stable internal source ids', () => {
        const first = AGENT_ROSTER_GROUPS[0]
        expect(first.id).toBe('posthog')
        expect(first.label).toBe('Flind data')
    })

    it('does not show any unconfigured inherited product documentation links', () => {
        const first = AGENT_ROSTER_GROUPS[0]
        for (const agent of first.agents) {
            if (agent.source !== 'health_checks') {
                expect(agent.docsUrl).toBeUndefined()
            }
        }
        expect(first.agents.find((entry) => entry.source === 'health_checks')?.docsUrl).toBeTruthy()
    })
})
