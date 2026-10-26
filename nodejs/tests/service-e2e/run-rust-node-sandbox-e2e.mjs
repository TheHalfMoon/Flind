#!/usr/bin/env node
// Explicit-entrypoint for the destructive Rust + production Node + Kafka +
// ClickHouse service E2E. Run only with user-owned ephemeral local services.
import { spawn } from 'node:child_process'
import { existsSync, statfsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { isolatedRustNodeE2E } from './rust-node-sandbox-admission.ts'

let sandbox
try {
    sandbox = isolatedRustNodeE2E(process.env)
} catch (error) {
    console.error('REFUSED: Rust/Node service E2E has no verified disposable sandbox:', error.message)
    process.exit(2)
}

// This prints no credentials, database URL, or other environment values.
if (process.argv.includes('--dry-run')) {
    console.log('PASS: isolated Flind service E2E configuration admitted; no services started or reset')
    process.exit(0)
}
if (process.argv.length !== 2) {
    console.error('REFUSED: unsupported service E2E arguments; use --dry-run for preflight')
    process.exit(2)
}

const here = path.dirname(fileURLToPath(import.meta.url))
const nodeRoot = path.resolve(here, '../..')
const jest = path.join(nodeRoot, 'node_modules', '.bin', 'jest')
if (!existsSync(jest)) {
    console.error('REFUSED: first-party frozen-lockfile Jest dependencies are unavailable')
    process.exit(2)
}

// Do not leak arbitrary connected-app/cloud credentials from the user's shell
// into a real Node worker. Only these local operating environment settings
// and the explicitly admitted loopback service configuration are inherited.
const processEnv = {}
for (const name of ['PATH', 'HOME', 'TMPDIR', 'LANG', 'TZ']) {
    if (process.env[name]) {
        processEnv[name] = process.env[name]
    }
}
for (const [key, value] of Object.entries(process.env)) {
    if (key.startsWith('FLIND_E2E_') && value) {
        processEnv[key] = value
    }
}
Object.assign(processEnv, {
    NODE_ENV: 'test',
    CI: 'true',
    TEST: '1',
    OTEL_SDK_DISABLED: 'true',
    DISABLE_OPENTELEMETRY_TRACING: 'true',
    NODE_OPTIONS: '--max-old-space-size=1800',
    ...sandbox.serviceEnv,
})

const cmd = [
    '--config',
    'jest.serial.config.js',
    '--runInBand',
    '--forceExit',
    '--testPathPatterns=service-e2e/rust-ingestion-consumer.serial.test.ts',
]
// Full service tests can compile Rust and start multiple local data engines.
// Fail closed before launch, then monitor the reserve while the child runs.
function freeDiskBytes() {
    const fs = statfsSync('/tmp')
    return fs.bavail * fs.bsize
}
if (freeDiskBytes() < 12 * 1024 ** 3) {
    console.error('REFUSED: at least 12 GiB free disk is required before full E2E')
    process.exit(2)
}

const child = spawn(jest, cmd, {
    cwd: nodeRoot,
    env: processEnv,
    stdio: 'inherit',
    detached: true,
})
let interrupted = false
const stop = (reason) => {
    if (interrupted) return
    interrupted = true
    console.error('STOPPING isolated E2E:', reason)
    try {
        // Kill the Jest *group*, including locally spawned worker processes.
        process.kill(-child.pid, 'SIGTERM')
    } catch {
        child.kill('SIGTERM')
    }
}
const diskWatch = setInterval(() => {
    try {
        if (freeDiskBytes() < 10 * 1024 ** 3) stop('10 GiB disk safety reserve reached')
    } catch {
        stop('could not verify free disk')
    }
}, 2000)
const timeout = setTimeout(() => stop('bounded local integration timeout'), 6 * 60 * 1000)
child.on('error', () => stop('Jest child failed to start'))
child.on('close', (code) => {
    clearInterval(diskWatch)
    clearTimeout(timeout)
    process.exit(interrupted ? 2 : (code ?? 2))
})
