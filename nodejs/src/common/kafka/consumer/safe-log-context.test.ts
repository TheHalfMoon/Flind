import { safeKafkaErrorContext, safeKafkaLogContext } from './safe-log-context'

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

describe('Kafka native diagnostic error privacy (Wave 94)', () => {
    it('keeps numeric codes and boolean flags without message, stack or tokens', () => {
        const secret = 'synthetic-super-secret'
        const native = Object.assign(new Error('SASL password=' + secret), {
            code: -172,
            errno: 13,
            origin: 'token=' + secret,
            isFatal: true,
            isRetriable: false,
            config: { 'sasl.password': secret, 'sasl.oauthbearer.config': secret },
        })
        const safe = safeKafkaErrorContext(native)
        expect(safe).toEqual({ errorCode: -172, errno: 13, isFatal: true, isRetriable: false })
        expect(JSON.stringify(safe)).not.toContain(secret)
    })

    it('ignores string error codes and any inherited secret-bearing properties', () => {
        const native = Object.assign(Object.create({ message: 'synthetic-inherited-secret' }), {
            code: 'secret-code',
            errno: 'secret-errno',
            isFatal: 'true',
            isRetriable: false,
        })
        expect(safeKafkaErrorContext(native)).toEqual({ isRetriable: false })
    })

    it('does not invoke String(error), custom toJSON or token-bearing exception messages', () => {
        const err = {
            code: 21,
            toString: () => { throw new Error('toString must not run') },
            toJSON: () => { throw new Error('toJSON must not run') },
        }
        expect(safeKafkaErrorContext(err)).toEqual({ errorCode: 21 })
        expect(safeKafkaErrorContext('SASL password secret')).toEqual({})
        expect(safeKafkaErrorContext(null)).toEqual({})
    })

    it('tolerates malicious error-field getters without throwing or leaking', () => {
        const err = {
            get code() { throw new Error('secret getter') },
            get errno() { throw new Error('secret getter') },
            get isFatal() { throw new Error('secret getter') },
            isRetriable: true,
        }
        expect(safeKafkaErrorContext(err)).toEqual({ isRetriable: true })
    })

    it('excludes NaN, infinity and unsafe numeric codes', () => {
        expect(safeKafkaErrorContext({ code: Number.NaN, errno: Infinity })).toEqual({})
        expect(safeKafkaErrorContext({ code: Number.MAX_SAFE_INTEGER + 1 })).toEqual({})
        expect(safeKafkaErrorContext({ code: 0, errno: 0, isFatal: false })).toEqual({
            errorCode: 0, errno: 0, isFatal: false,
        })
    })
})
