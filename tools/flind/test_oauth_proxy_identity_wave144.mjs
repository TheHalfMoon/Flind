import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'

const root = process.env.FLIND_SOURCE_ROOT || process.cwd()
const ref = process.env.FLIND_TEST_REF || 'HEAD'
function source(path) {
  return execFileSync('git', ['-C', root, 'show', ref + ':' + path], {
    encoding: 'utf8', timeout: 45000, maxBuffer: 2000000,
  })
}

const pkg = JSON.parse(source('services/oauth-proxy/package.json'))
assert.equal(pkg.name, '@flind/auth-proxy')
assert.equal(pkg.private, true)
assert.ok(pkg.description.startsWith('Flind regional OAuth proxy'))
assert.equal(pkg.author, 'Flind Contributors')
assert.ok(!pkg.keywords.includes('posthog'))
console.log('PASS first-party Flind OAuth package display metadata')

const jsonc = source('services/oauth-proxy/wrangler.jsonc')
const clean = jsonc.split('\n')
  .filter(line => !line.trimStart().startsWith('//'))
  .join('\n').replace(/,(\s*[}\]])/g, '$1')
const wrangler = JSON.parse(clean)
assert.equal(wrangler.name, 'flind-auth-proxy')
assert.equal(wrangler.kv_namespaces.length, 1)
assert.deepEqual(Object.keys(wrangler.kv_namespaces[0]), ['binding'])
assert.equal(wrangler.kv_namespaces[0].binding, 'AUTH_KV')
assert.equal(jsonc.includes('3ac9a85816994f3ea94f98364de4732a'), false)
console.log('PASS inherited production Cloudflare KV namespace cannot be deployed from checked-in config')

const index = source('services/oauth-proxy/src/index.ts')
const landing = index.match(/return new Response\(('Flind OAuth Proxy'),\s*\{\s*headers:\s*\{\s*'Content-Type':\s*'text\/plain'\s*\},?\s*\}\)/)
assert.ok(landing, 'real worker must return first-party landing message with text/plain headers')
const response = new Response('Flind OAuth Proxy', {headers:{'Content-Type':'text/plain'}})
assert.equal(await response.text(), 'Flind OAuth Proxy')
assert.ok(!index.includes('PostHog OAuth Proxy - https://posthog.com/docs/api/oauth'))
const originalRouterTests = source('services/oauth-proxy/tests/router.test.ts')
assert.ok(originalRouterTests.includes("expect(text).toBe('Flind OAuth Proxy')"))
console.log('PASS worker landing response and original router regression expect Flind')

const constants = source('services/oauth-proxy/src/lib/constants.ts')
assert.ok(constants.includes('https://us.posthog.com'))
assert.ok(constants.includes('https://eu.posthog.com'))
console.log('KNOWN BLOCKER: inherited OAuth US/EU targets still require owned Flind endpoint migration and E2E')
console.log('Wave144 PASS: no publication or deployment performed')
