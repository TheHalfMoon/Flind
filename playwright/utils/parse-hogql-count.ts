/**
 * Validate the shape of a HogQL count() response before interpreting zero as tenant isolation.
 * A malformed or absent response must never silently pass a negative-control security test.
 */
export function parseHogQLCount(response: unknown): number {
    if (response === null || typeof response !== 'object') {
        throw new Error('HogQL response is missing or not an object')
    }
    const rows: unknown = (response as { results?: unknown }).results
    if (!Array.isArray(rows) || rows.length !== 1 || !Array.isArray(rows[0]) || rows[0].length !== 1) {
        throw new Error('HogQL count() must return exactly one row and one column')
    }
    const rawCount: unknown = rows[0][0]
    if (typeof rawCount !== 'number' && typeof rawCount !== 'string') {
        throw new Error('HogQL count() was not a number or numeric string')
    }
    if (typeof rawCount === 'string' && !/^\d+$/.test(rawCount)) {
        throw new Error('HogQL count() returned a non-numeric string')
    }
    const count = Number(rawCount)
    if (!Number.isSafeInteger(count) || count < 0) {
        throw new Error('HogQL count() was not a non-negative safe integer')
    }
    return count
}
