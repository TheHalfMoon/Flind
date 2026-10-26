import { spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import path from 'node:path'

/**
 * Test-only preflight for the actual Rust -> production Node service E2E.
 * Run with the exact PATH that Jest will inherit (its shebang uses env node).
 * Do not continue into destructive fixtures if native Kafka/RE2 cannot load
 * or the production worker's TypeScript launcher is absent.
 */
export function requireNativeServiceE2ERuntime(nodeRoot, childEnv) {
    if (!existsSync(path.join(nodeRoot, 'node_modules', '.bin', 'jest'))) {
        throw new Error('First-party Jest dependency missing from isolated Node workspace')
    }

    const probe = spawnSync(
        'node',
        [
            '-e',
            "for (const name of ['node-rdkafka', 're2']) require(name); require.resolve('tsx')",
        ],
        {
            cwd: nodeRoot,
            env: childEnv,
            timeout: 12_000,
            stdio: 'ignore',
        }
    )
    if (probe.error || probe.status !== 0) {
        // Node/native compiler diagnostics may contain usernames or paths;
        // never emit the child process output or its environment.
        throw new Error('Isolated Node worker native dependencies unavailable or incompatible')
    }
}
