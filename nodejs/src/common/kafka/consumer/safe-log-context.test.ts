import { safeKafkaLogContext } from './safe-log-context'

describe('Kafka consumer operational log allowlist', () => {
    it('emits only non-credential routing coordinates', () => {
        const config = {
            topic: 'test-events',
            groupId: 'test-ingestion',
            'sasl.password': 'synthetic-sasl-secret',
            'ssl.key.password': 'synthetic-tls-secret',
            'sasl.oauthbearer.config': 'synthetic-oauth-token',
            extra: { authorization: 'Bearer synthetic-token' },
        }
        const result = safeKafkaLogContext(config)
        expect(result).toEqual({ topic: 'test-events', groupId: 'test-ingestion' })
        const serialized = JSON.stringify(result)
        for (const secret of ['synthetic-sasl-secret', 'synthetic-tls-secret', 'synthetic-oauth-token', 'synthetic-token']) {
            expect(serialized).not.toContain(secret)
        }
    })

    it('creates a fresh, narrowly shaped object rather than preserving original config', () => {
        const config = {
            topic: 'test-events',
            groupId: 'test-ingestion',
            'sasl.password': 'synthetic-secret',
        }
        const result = safeKafkaLogContext(config)
        expect(Object.keys(result).sort()).toEqual(['groupId', 'topic'])
        expect(result).not.toBe(config)
        expect(config['sasl.password']).toBe('synthetic-secret')
    })

    it('does not propagate inherited enumerable configuration fields', () => {
        const input = Object.assign(
            Object.create({ 'ssl.key.password': 'synthetic-inherited-secret' }) as {topic: string; groupId: string},
            { topic: 'test-events', groupId: 'test-ingestion' }
        )
        expect(Object.keys(safeKafkaLogContext(input)).sort()).toEqual(['groupId', 'topic'])
    })
})
