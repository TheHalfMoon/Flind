import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const compose = readFileSync(new URL('../../docker-compose.dev.yml', import.meta.url), 'utf8')
const workflow = readFileSync(new URL('../../.github/workflows/flind-e2e.yml', import.meta.url), 'utf8')
const base = readFileSync(new URL('../../docker-compose.base.yml', import.meta.url), 'utf8')

test('only local loopback is published to the host on the development proxy port', () => {
    assert.match(compose, /^\s+- 127\.0\.0\.1:8010:8000$/m)
    assert.doesNotMatch(compose, /^\s+- (?:0\.0\.0\.0:)?8010:8000$/m)
})

test('Caddy dev site names explicitly match localhost and numeric HTTP loopback, never a catch-all', () => {
    assert.match(compose, /\$\{CADDY_HOST:-http:\/\/localhost:8000, http:\/\/127\.0\.0\.1:8000\} \{/)
    assert.doesNotMatch(compose, /CADDY_HOST:-http:\/\/:8000/)
    assert.doesNotMatch(compose, /CADDY_HOST:-http:\/\/0\.0\.0\.0:8000/)
    assert.match(base, /CADDY_HOST: 'http:\/\/localhost:8000'/)
})

test('both numeric and hostname origins share explicit capture paths and the same Rust collector', () => {
    assert.match(compose, /path \/batch/)
    assert.match(compose, /path \/capture/)
    assert.match(compose, /reverse_proxy capture:3307/)
    assert.match(compose, /handle @capture \{/)
})

test('real test stack must verify both Host routes, not just match a source string', () => {
    assert.match(workflow, /'flind-ci\/dev-proxy-loopback-\*'/)
    assert.match(workflow, /node --test frontend\/bin\/flind-dev-proxy-loopback\.test\.mjs/)
    assert.match(workflow, /curl --fail --silent --show-error --retry 10 --retry-delay 1 http:\/\/localhost:8010\/_health/)
    assert.match(workflow, /curl --fail --silent --show-error --retry 10 --retry-delay 1 http:\/\/127\.0\.0\.1:8010\/_health/)
    assert.match(workflow, /docker compose -f docker-compose\.dev\.yml up -d --wait --wait-timeout 90 proxy/)
})
