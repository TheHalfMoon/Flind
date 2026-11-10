import posthog from 'posthog-js'

import api from 'lib/api'
import { flindRegionHost, type FlindRegionHosts } from 'lib/flindRegionHosts'
import { hogql } from 'lib/utils/hogql'

import { HogQLQueryResponse, NodeKind, QueryLogTags } from '~/queries/schema/schema-general'
import { Region } from '~/types'

// EU users have no rows in this region's posthog_user tables; eu_org_members is a
// materialized DWH pre-join of the EU postgres sync (prod-only, refreshed daily).
const EU_ORG_MEMBERS_VIEW = 'eu_org_members'

/** Never redirect an admin action to an inherited or unregistered cloud host.
 * Cross-region links are only produced between operator-configured Flind region hosts;
 * otherwise the link stays on the current origin.
 */
export function getUserAdminUrl(
    region: Region.US | Region.EU,
    userId: number,
    currentOrigin: string = window.location.origin,
    configuredHosts?: FlindRegionHosts
): string {
    const currentUrl = new URL(currentOrigin)
    const target = flindRegionHost(region, configuredHosts)
    const ownedRegions = ([Region.US, Region.EU] as const)
        .map((r) => flindRegionHost(r, configuredHosts))
        .filter((host): host is string => !!host)
    const currentIsConfiguredFlindRegion = ownedRegions.some((host) => currentUrl.origin === `https://${host}`)
    const adminOrigin = currentIsConfiguredFlindRegion && target ? `https://${target}` : currentUrl.origin

    return `${adminOrigin}/admin/posthog/user/${userId}/change/`
}

export function isEuOrgMembersViewMissingError(error: unknown): boolean {
    const message = error instanceof Error ? error.message : String(error ?? '')
    return (
        message.includes(EU_ORG_MEMBERS_VIEW) &&
        (message.includes("don't have access to table") || message.includes('Unknown table'))
    )
}

export async function getEuUserId(distinctIds: string[], tags: QueryLogTags): Promise<number | null> {
    try {
        const response = (await api.query({
            kind: NodeKind.HogQLQuery,
            tags,
            query: hogql`
                select user_id
                from eu_org_members
                where distinct_id in ${distinctIds}
                limit 1
            `,
        })) as HogQLQueryResponse
        const userId = response.results?.[0]?.[0]
        return userId == null ? null : Number(userId)
    } catch (error) {
        if (!isEuOrgMembersViewMissingError(error)) {
            posthog.captureException(error as Error, { scope: 'userAdmin.getEuUserId' })
        }
        return null
    }
}
