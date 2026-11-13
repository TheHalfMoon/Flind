import { expect, type APIRequestContext } from '@playwright/test'

/**
 * Positive event persistence + an unrelated user's successful zero-count query
 * do not prove authorization. Try to query the target team's data using the
 * other workspace's valid personal API key and require an actual denial.
 *
 * The caller must first prove both principals can query their own teams.
 * We deliberately do not log keys, event names, response bodies or URLs.
 */
export async function assertForeignPersonalKeyCannotQueryTeam(
    request: APIRequestContext,
    targetTeamId: string,
    foreignPersonalApiKey: string,
    eventName: string
): Promise<void> {
    if (!/^\d+$/.test(targetTeamId) || !/^[A-Za-z0-9_-]+$/.test(eventName)) {
        throw new Error('Invalid synthetic team ID or event name for tenant-boundary probe')
    }
    const response = await request.post(`/api/environments/${targetTeamId}/query/`, {
        headers: { Authorization: `Bearer ${foreignPersonalApiKey}` },
        // Do not accept a denial returned by an unrelated redirect target.
        maxRedirects: 0,
        data: {
            refresh: 'force_blocking',
            query: {
                kind: 'HogQLQuery',
                query: `SELECT count() FROM events WHERE event = '${eventName}'`,
            },
        },
    })
    // Any successful response (even a count of zero) means the wrong
    // principal reached the query endpoint. Fail rather than trusting
    // downstream HogQL filtering alone.
    expect([401, 403, 404], 'foreign workspace credentials must be rejected before querying').toContain(response.status())
}
