import assert from 'node:assert/strict'
import { mkdtempSync, mkdirSync, rmSync, writeFileSync, readFileSync } from 'node:fs'
import os from 'node:os'
import path from 'node:path'

import { requireNativeServiceE2ERuntime } from '../../nodejs/tests/service-e2e/native-runtime-preflight.mjs'

const tmp = mkdtempSync(path.join(os.tmpdir(), 'flind-wave132-node-'))
const modules = path.join(tmp, 'node_modules')
const env = {
    PATH: process.env.PATH,
    HOME: tmp,
    LANG: 'C',
    NODE_OPTIONS: '--max-old-space-size=512',
}
function moduleFile(name, code = 'module.exports = {}') {
    const dir = path.join(modules, name)
    mkdirSync(dir, { recursive: true })
    writeFileSync(path.join(dir, 'index.js'), code)
}
function failsWithoutSecrets() {
    assert.throws(() => requireNativeServiceE2ERuntime(tmp, env),
        (error) => error instanceof Error &&
            error.message.includes('unavailable or incompatible') &&
            !error.message.includes('SECRET'))
}
try {
    // No Jest => refuse before invoking even the benign native probe.
    assert.throws(() => requireNativeServiceE2ERuntime(tmp, env), /Jest dependency missing/)
    mkdirSync(path.join(modules, '.bin'), { recursive: true })
    writeFileSync(path.join(modules, '.bin', 'jest'), '')

    failsWithoutSecrets() // all 3 Node worker prerequisites missing
    moduleFile('node-rdkafka')
    moduleFile('re2')
    failsWithoutSecrets() // tsx is required too
    moduleFile('tsx')
    assert.doesNotThrow(() => requireNativeServiceE2ERuntime(tmp, env))

    moduleFile('re2', "throw new Error('SECRET_NATIVE_ABI_FAILURE')")
    failsWithoutSecrets() // native load error is sanitized
    moduleFile('re2')
    assert.doesNotThrow(() => requireNativeServiceE2ERuntime(tmp, env))

    const runner = readFileSync(new URL('../../nodejs/tests/service-e2e/run-rust-node-sandbox-e2e.mjs', import.meta.url), 'utf8')
    const guard = runner.lastIndexOf('requireNativeServiceE2ERuntime(nodeRoot, processEnv)')
    const launch = runner.indexOf('const child = spawn(jest')
    assert.ok(guard !== -1 && launch > guard)
    console.log('Wave132 PASS: isolated native runtime admission and sanitized fail-closed cases')
} finally {
    rmSync(tmp, { recursive: true, force: true })
}
