import { useQuery } from '@tanstack/react-query'

import { type RegionId, regionForHost } from '@/auth/regions'
import { useDataMode } from '@/demo/demoMode'

/**
 * Status pages must be configured by the Flind operator. A missing or invalid
 * destination disables external status checks rather than showing a donor page.
 */
export function flindStatusOrigin(value: string | undefined): string | null {
    if (!value?.trim()) return null
    try {
        const url = new URL(value.trim())
        const host = url.hostname.toLowerCase().replace(/\.$/, '')
        if (
            url.protocol !== 'https:' ||
            url.username ||
            url.password ||
            url.port ||
            url.pathname !== '/' ||
            url.search ||
            url.hash ||
            host === 'posthog.com' ||
            host.endsWith('.posthog.com') ||
            host === 'posthog.dev' ||
            host.endsWith('.posthog.dev') ||
            host === 'posthogstatus.com' ||
            host.endsWith('.posthogstatus.com')
        ) {
            return null
        }
        return url.origin
    } catch {
        return null
    }
}
const FIVE_MINUTES = 5 * 60_000

// incident.io uses full_outage for the state the web app calls a major outage.
const impactLabels = {
    degraded_performance: 'Degraded performance',
    partial_outage: 'Partial outage',
    full_outage: 'Major outage',
} as const
type Impact = keyof typeof impactLabels
type IncidentPhase = 'investigating' | 'identified' | 'monitoring'
const impactRank: Record<Impact | 'operational', number> = {
    operational: 0,
    degraded_performance: 1,
    partial_outage: 2,
    full_outage: 3,
}

interface Component {
    current_status: Impact | 'operational'
    group_name?: string
    name: string
}

interface StatusEvent {
    name: string
    affected_components: Component[]
}

interface Summary {
    ongoing_incidents: (StatusEvent & {
        id: string
        current_worst_impact: Impact
        status: IncidentPhase
    })[]
    in_progress_maintenances: StatusEvent[]
}

function incidentColor(impact: Component['current_status']): 'yellow' | 'diffRed' {
    return impact === 'partial_outage' || impact === 'full_outage' ? 'diffRed' : 'yellow'
}

export interface PostHogStatus {
    indicatorColor?: 'diffGreen' | ReturnType<typeof incidentColor>
    pageUrl: string | null
    summary?: string
    aiIncident?: { title: string; url: string; status: IncidentPhase; color: ReturnType<typeof incidentColor> }
}

export function regionalStatus(
    summary: Summary,
    region: 'us' | 'eu',
    statusOrigin: string | null = flindStatusOrigin(process.env.EXPO_PUBLIC_FLIND_STATUS_URL)
): PostHogStatus {
    const group = region === 'us' ? 'US Cloud' : 'EU Cloud'
    const inRegion = (component: Component): boolean =>
        component.group_name?.replace(/[^\p{L}\p{N}\s]/gu, '').trim() === group
    const relevant = (event: StatusEvent): boolean =>
        event.affected_components.length === 0 || event.affected_components.some(inRegion)
    const incidents = summary.ongoing_incidents
        .filter(relevant)
        .sort((a, b) => impactRank[b.current_worst_impact] - impactRank[a.current_worst_impact])
    const incident = incidents[0]
    const maintenance = summary.in_progress_maintenances.find(relevant)
    const [ai] = incidents
        .flatMap((event) => {
            const component = event.affected_components.find((item) => item.name === 'Flind AI' && inRegion(item))
            return component ? [{ event, impact: component.current_status }] : []
        })
        .sort((a, b) => impactRank[b.impact] - impactRank[a.impact])
    const impact = incident && impactLabels[incident.current_worst_impact]
    const count = incidents.length > 1 ? ` (${incidents.length} incidents)` : ''
    return {
        pageUrl: statusOrigin ? `${statusOrigin}/${region}` : null,
        indicatorColor: incident ? incidentColor(incident.current_worst_impact) : maintenance ? 'yellow' : 'diffGreen',
        summary: incident
            ? `${impact ?? 'Incident'}${count} · ${incident.name}`
            : maintenance && `Maintenance in progress · ${maintenance.name}`,
        aiIncident:
            ai && statusOrigin
                ? {
                      title: ai.event.name,
                      color: incidentColor(ai.impact),
                      status: ai.event.status,
                      url: `${statusOrigin}/incidents/${encodeURIComponent(ai.event.id)}`,
                  }
                : undefined,
    }
}

export function usePostHogStatus(host: string | undefined): PostHogStatus {
    const mode = useDataMode()
    const statusOrigin = flindStatusOrigin(process.env.EXPO_PUBLIC_FLIND_STATUS_URL)
    const region: RegionId = mode === 'live' && statusOrigin && host ? regionForHost(host) : 'custom'
    const { data } = useQuery({
        queryKey: ['flind-status', statusOrigin, region],
        enabled: Boolean(statusOrigin) && region !== 'custom',
        queryFn: async ({ signal }): Promise<PostHogStatus> => {
            if (!statusOrigin || region === 'custom') return { pageUrl: null }
            const response = await fetch(`${statusOrigin}/api/v1/summary`, {
                signal,
                credentials: 'omit',
                redirect: 'error',
            })
            if (!response.ok) throw new Error(`Status page returned ${response.status}`)
            return regionalStatus(await response.json(), region, statusOrigin)
        },
        staleTime: FIVE_MINUTES,
        refetchInterval: FIVE_MINUTES,
        refetchOnWindowFocus: true,
    })
    return data ?? { pageUrl: region === 'custom' ? null : `${statusOrigin}/${region}` }
}
