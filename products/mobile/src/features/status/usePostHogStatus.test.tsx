test.each([
    [undefined, null],
    ['', null],
    ['http://status.flind.example', null],
    ['https://www.posthogstatus.com', null],
    ['https://posthogstatus.com', null],
    ['https://posthog.com', null],
    ['https://admin:secret@status.flind.example', null],
    ['https://status.flind.example/path', null],
    ['https://status.flind.example', STATUS],
])('accepts only explicitly configured non-donor HTTPS status origins: %s', (input, expected) => {
    expect(flindStatusOrigin(input)).toBe(expected)
})

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react-native'
import type { PropsWithChildren, ReactElement } from 'react'

import { useDataMode } from '@/demo/demoMode'

import { flindStatusOrigin, regionalStatus, usePostHogStatus } from './usePostHogStatus'

jest.mock('@/demo/demoMode', () => ({ useDataMode: jest.fn(() => 'live') }))
jest.mock('@/auth/regions', () => ({
    regionForHost: (host: string) => (host === 'https://eu.flind.example' ? 'eu' : 'custom'),
}))

const STATUS = 'https://status.flind.example'


const euAI = { current_status: 'degraded_performance' as const, name: 'Flind AI', group_name: 'EU Cloud 🇪🇺' }
const usAPI = { current_status: 'degraded_performance' as const, name: 'API', group_name: 'US Cloud 🇺🇸' }
const incident = {
    current_worst_impact: 'degraded_performance' as const,
    status: 'investigating' as const,
    id: 'incident-123',
    name: 'Elevated error rate',
    affected_components: [euAI, usAPI],
}
const summary = { ongoing_incidents: [incident], in_progress_maintenances: [] }

test('shows a cross-region incident in both menus but only in the affected AI chat', () => {
    expect(regionalStatus(summary, 'us', STATUS)).toEqual({
        pageUrl: 'https://status.flind.example/us',
        indicatorColor: 'yellow',
        summary: `Degraded performance · ${incident.name}`,
    })
    expect(regionalStatus(summary, 'eu', STATUS).aiIncident).toEqual({
        title: incident.name,
        color: 'yellow',
        status: incident.status,
        url: 'https://status.flind.example/incidents/incident-123',
    })
})

test('global incidents and maintenance appear in the menu without implying AI is affected', () => {
    const global = { ...incident, affected_components: [] }
    const maintenance = { name: 'Database maintenance', affected_components: [euAI] }
    const events = { ongoing_incidents: [global], in_progress_maintenances: [maintenance] }
    expect(regionalStatus(events, 'us', STATUS).summary).toBe(`Degraded performance · ${global.name}`)
    expect(regionalStatus(events, 'eu', STATUS).aiIncident).toBeUndefined()
    const resolved = { ...events, ongoing_incidents: [] }
    expect(regionalStatus(resolved, 'us', STATUS).indicatorColor).toBe('diffGreen')
    expect(regionalStatus(resolved, 'eu', STATUS).indicatorColor).toBe('yellow')
    expect(regionalStatus(resolved, 'us', STATUS).summary).toBeUndefined()
    expect(regionalStatus(resolved, 'eu', STATUS).summary).toBe(`Maintenance in progress · ${maintenance.name}`)
    expect(regionalStatus(resolved, 'eu', STATUS).aiIncident).toBeUndefined()
})

test('clears a resolved AI incident and skips status requests in demo and self-hosted sessions', async () => {
    process.env.EXPO_PUBLIC_FLIND_STATUS_URL = STATUS
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const fetchStatus = jest.spyOn(global, 'fetch').mockResolvedValue(Response.json(summary))
    function wrapper({ children }: PropsWithChildren): ReactElement {
        return <QueryClientProvider client={client}>{children}</QueryClientProvider>
    }
    const hook = renderHook((host: string) => usePostHogStatus(host), {
        initialProps: 'https://eu.flind.example',
        wrapper,
    })
    try {
        await waitFor(() => expect(hook.result.current.aiIncident?.title).toBe(incident.name))
        fetchStatus.mockResolvedValue(Response.json({ ongoing_incidents: [], in_progress_maintenances: [] }))
        await act(() => client.invalidateQueries({ queryKey: ['flind-status'] }))
        await waitFor(() => expect(hook.result.current.aiIncident).toBeUndefined())
        fetchStatus.mockClear()
        hook.rerender('https://self-hosted.example.com')
        expect(hook.result.current).toEqual({ pageUrl: null })
        jest.mocked(useDataMode).mockReturnValue('demo')
        hook.rerender('https://eu.flind.example')
        expect(hook.result.current).toEqual({ pageUrl: null })
        expect(fetchStatus).not.toHaveBeenCalled()
    } finally {
        hook.unmount()
        client.clear()
        fetchStatus.mockRestore()
        jest.mocked(useDataMode).mockReturnValue('live')
        delete process.env.EXPO_PUBLIC_FLIND_STATUS_URL
    }
})

test('ranks the regional outage separately from the AI component and updates as incidents change', () => {
    const partial = {
        ...incident,
        id: 'partial',
        name: 'AI requests failing',
        current_worst_impact: 'partial_outage' as const,
        affected_components: [{ ...euAI, current_status: 'partial_outage' as const }],
    }
    const major = { ...incident, id: 'major', name: 'API unavailable', current_worst_impact: 'full_outage' as const }
    const majorStatus = regionalStatus({ ...summary, ongoing_incidents: [major] }, 'eu', STATUS)
    expect(majorStatus.indicatorColor).toBe('diffRed')
    expect(majorStatus.aiIncident?.color).toBe('yellow')
    const events = { ...summary, ongoing_incidents: [incident, partial, major] }
    expect(regionalStatus(events, 'eu', STATUS).summary).toBe('Major outage (3 incidents) · API unavailable')
    expect(regionalStatus(events, 'eu', STATUS).indicatorColor).toBe('diffRed')
    expect(regionalStatus(events, 'eu', STATUS).aiIncident?.color).toBe('diffRed')
    expect(regionalStatus(events, 'eu', STATUS).aiIncident?.title).toBe(partial.name)
    const monitoring = { ...partial, status: 'monitoring' as const }
    const remaining = { ...summary, ongoing_incidents: [monitoring] }
    expect(regionalStatus(remaining, 'eu').indicatorColor).toBe('diffRed')
    expect(regionalStatus(remaining, 'eu').summary).toBe('Partial outage · AI requests failing')
    expect(regionalStatus(remaining, 'eu').aiIncident?.status).toBe('monitoring')
    expect(regionalStatus(remaining, 'us').summary).toBeUndefined()
})
