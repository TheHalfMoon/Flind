/**
 * Fail-closed Flind mobile live-stats routing.
 *
 * No separate Flind-owned stats service is deployed and verified. Upstream
 * US/EU hostnames belong to another operator: never send Flind tokens to them.
 * The Live screen already supports a project-scoped HogQL usersOnline query.
 */
export interface LiveStatsApi {
    users_on_product?: number | null
}

export class LiveStatsError extends Error {
    constructor(status: number) {
        super(`Live stats failed with status ${status}`)
        this.name = 'LiveStatsError'
    }
}

/** No upstream or custom host can become a token recipient implicitly. */
export function liveStatsHost(_environmentHost: string): null {
    return null
}

/** Reject before network or token use, including if invoked outside LiveScreen. */
export function fetchLiveStats(_liveHost: string, _token: string, _signal?: AbortSignal): Promise<LiveStatsApi> {
    return Promise.reject(new Error('Flind live stats endpoint is not configured; use the scoped HogQL usersOnline query'))
}
