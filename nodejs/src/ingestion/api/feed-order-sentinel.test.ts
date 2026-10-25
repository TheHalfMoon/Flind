import { logger } from '~/common/utils/logger'

import { FeedOrderSentinel } from './feed-order-sentinel'
import { SerializedKafkaMessage } from './types'

function msg(offset: number, overrides: Partial<SerializedKafkaMessage> = {}): SerializedKafkaMessage {
    return {
        topic: 'events',
        partition: 0,
        offset,
        timestamp: 0,
        key: 't:a',
        value: null,
        headers: {},
        ...overrides,
    }
}

describe('FeedOrderSentinel', () => {
    it('passes messages fed in ascending offset order per key', () => {
        const sentinel = new FeedOrderSentinel()
        expect(sentinel.check([msg(1), msg(2)], 'c1', false)).toEqual({ outOfOrder: 0, replayed: 0 })
        expect(sentinel.check([msg(3)], 'c1', false)).toEqual({ outOfOrder: 0, replayed: 0 })
    })

    it('flags an offset regression within one consumer incarnation', () => {
        const sentinel = new FeedOrderSentinel()
        sentinel.check([msg(5)], 'c1', false)
        expect(sentinel.check([msg(3)], 'c1', false)).toEqual({ outOfOrder: 1, replayed: 0 })
    })

    it('counts a regression in a replay request as replayed, not a violation', () => {
        const sentinel = new FeedOrderSentinel()
        sentinel.check([msg(5)], 'c1', false)
        expect(sentinel.check([msg(5)], 'c1', true)).toEqual({ outOfOrder: 0, replayed: 1 })
    })

    it('rebaselines when the consumer incarnation changes', () => {
        const sentinel = new FeedOrderSentinel()
        sentinel.check([msg(100)], 'c1', false)
        // A restarted consumer replays from the last commit — not a violation.
        expect(sentinel.check([msg(50)], 'c2', false)).toEqual({ outOfOrder: 0, replayed: 0 })
        // But the new incarnation is now the baseline.
        expect(sentinel.check([msg(40)], 'c2', false)).toEqual({ outOfOrder: 1, replayed: 0 })
    })

    it('tracks keys independently across partitions and Kafka keys', () => {
        const sentinel = new FeedOrderSentinel()
        sentinel.check([msg(10), msg(10, { partition: 1 }), msg(10, { key: 't:b' })], 'c1', false)
        // Same offsets again on other keys don't interfere; only 'a' on partition 0 regresses.
        expect(sentinel.check([msg(9)], 'c1', false)).toEqual({ outOfOrder: 1, replayed: 0 })
        expect(sentinel.check([msg(11, { partition: 1 })], 'c1', false)).toEqual({ outOfOrder: 0, replayed: 0 })
    })

    it.each([null, ''])('skips unkeyed messages even when routing headers are present (key: %j)', (key) => {
        const sentinel = new FeedOrderSentinel()
        const headers = { token: 't', distinct_id: 'a' }
        const result = sentinel.check([msg(5, { key, headers }), msg(1, { key, headers })], 'c1', false)
        expect(result).toEqual({ outOfOrder: 0, replayed: 0 })
        expect(sentinel.size).toBe(0)
    })

    it('does not alias different topic/partition/key tuples containing slashes', () => {
        const sentinel = new FeedOrderSentinel()
        // Previously both identities serialized to 'events/1/2/customer'.
        // Even unexpected upstream topic strings must not share a baseline.
        const first = msg(100, { topic: 'events/1', partition: 2, key: 'customer' })
        const second = msg(5, { topic: 'events', partition: 1, key: '2/customer' })
        expect(sentinel.check([first, second], 'c1', false)).toEqual({ outOfOrder: 0, replayed: 0 })
        expect(sentinel.size).toBe(2)
        expect(sentinel.check([msg(4, { topic: 'events', partition: 1, key: '2/customer' })], 'c1', false)).toEqual({
            outOfOrder: 1,
            replayed: 0,
        })
    })

    it('does not write sensitive capture tokens or distinct IDs into warning logs', () => {
        const warn = jest.spyOn(logger, 'warn').mockImplementation(() => undefined)
        try {
            const privateKey = 'private-capture-token:user@example.invalid'
            const secretMessage = msg(100, { key: privateKey, topic: 'events' })
            sentinelCaptureWarning(secretMessage)
            expect(warn).toHaveBeenCalledTimes(1)
            expect(warn.mock.calls[0][2]).toEqual({
                topic: 'events',
                partition: 0,
                offset: 99,
                lastSeenOffset: 100,
                consumerId: 'c1',
            })
            const serialized = JSON.stringify(warn.mock.calls)
            expect(serialized).not.toContain('private-capture-token')
            expect(serialized).not.toContain('user@example.invalid')
        } finally {
            warn.mockRestore()
        }

        function sentinelCaptureWarning(message: SerializedKafkaMessage): void {
            const sentinel = new FeedOrderSentinel()
            sentinel.check([message], 'c1', false)
            sentinel.check([{ ...message, offset: message.offset - 1 }], 'c1', false)
        }
    })

    it('evicts the least-recently-seen key at capacity and rebaselines it silently', () => {
        const sentinel = new FeedOrderSentinel(2)
        sentinel.check([msg(10)], 'c1', false)
        sentinel.check([msg(10, { key: 't:b' })], 'c1', false)
        sentinel.check([msg(10, { key: 't:c' })], 'c1', false)
        expect(sentinel.size).toBe(2)
        // 'a' was evicted: its regression rebaselines instead of firing.
        expect(sentinel.check([msg(5)], 'c1', false)).toEqual({ outOfOrder: 0, replayed: 0 })
    })
})
