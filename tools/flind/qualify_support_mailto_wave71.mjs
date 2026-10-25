import assert from 'node:assert/strict'
import { pathToFileURL } from 'node:url'
import { resolve } from 'node:path'

const file = pathToFileURL(resolve('frontend/src/lib/flindSupportMailto.ts')).href
const { flindSupportMailto } = await import(file)

const valid = 'mailto:help@flind.example?subject=Flind%20support%20request'
assert.equal(flindSupportMailto('help@flind.example', 'flind.example'), valid)
assert.equal(flindSupportMailto('help+urgent@flind.example', 'flind.example'),
    'mailto:help+urgent@flind.example?subject=Flind%20support%20request')
for (const [email, domain] of [
    [undefined, undefined],
    ['', 'flind.example'],
    ['help@flind.example', undefined],
    ['help@other.example', 'flind.example'],
    ['help@flind.example.attacker.example', 'flind.example'],
    ['help@flind.example?cc=evil@example.com', 'flind.example'],
    ['help@flind.example%0aBCC:evil', 'flind.example'],
    ['help@flind.example\n', 'flind.example'],
    ['.help@flind.example', 'flind.example'],
    ['help..desk@flind.example', 'flind.example'],
    ['help@flind.example', 'flind.example/path'],
    ['help@flind.example', '-flind.example'],
    ['support@posthog.com', 'posthog.com'],
    ['help@flind.example', 'flind.example.evil'],
    [false, 'flind.example'],
    ['help@flind.example', 123],
]) {
    assert.equal(flindSupportMailto(email, domain), null, String(email))
}

console.log('PASS: 18 exact-source support mailbox admission checks')
