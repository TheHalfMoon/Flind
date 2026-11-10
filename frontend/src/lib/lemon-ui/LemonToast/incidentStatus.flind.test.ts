import { configuredStatusPageHost, STATUS_PAGE_BASE } from './incidentStatus'

describe('Flind incident status host isolation', () => {
    it('does not read any inherited public incident feed by default', () => {
        expect(STATUS_PAGE_BASE).toBe('')
        expect(configuredStatusPageHost('')).toBeNull()
    })

    it('accepts only bare first-party HTTPS host names configured by the operator', () => {
        expect(configuredStatusPageHost('status.flind.example')).toBe('status.flind.example')
    })

    it.each([
        'https://status.flind.example',
        'status.flind.example/summary',
        'user@status.flind.example',
        'status.flind.example:443',
        'STATUS.FLIND.EXAMPLE',
        'status..flind.example',
        '-bad.flind.example',
        '',
    ])('refuses a malformed or URL-shaped host: %s', (host) => {
        expect(configuredStatusPageHost(host)).toBeNull()
    })
})
