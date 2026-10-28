import { lstatSync, mkdtempSync, readFileSync, realpathSync, rmSync, statfsSync, writeFileSync } from 'node:fs'
import path from 'node:path'

const PREFIX = '.flind-rust-node-e2e-'
const MARKER = 'FLIND_RUST_NODE_E2E_SCRATCH_V1\n'
const REQUIRED_FREE = 12 * 1024 ** 3

function freeBytes(dir) {
    const stats = statfsSync(dir)
    return stats.bavail * stats.bsize
}

/** Keep temporary test artifacts on the checkout volume, not a small /tmp tmpfs. */
export function createOwnedLocalScratch(repoRoot, { requiredBytes = REQUIRED_FREE } = {}) {
    const root = path.resolve(repoRoot)
    const parent = path.dirname(root)
    if (lstatSync(root).isSymbolicLink() || !lstatSync(root).isDirectory()) {
        throw new Error('Flind source checkout must be a real directory')
    }
    if (lstatSync(parent).isSymbolicLink() || !lstatSync(parent).isDirectory()) {
        throw new Error('Flind scratch parent must be a real directory')
    }
    if (realpathSync(root) !== root || realpathSync(parent) !== parent) {
        throw new Error('Flind scratch parent cannot traverse symbolic links')
    }
    if (freeBytes(parent) < requiredBytes) {
        throw new Error('Flind scratch filesystem lacks the required 12 GiB reserve')
    }
    const dir = mkdtempSync(path.join(parent, PREFIX))
    let marked = false
    try {
        writeFileSync(path.join(dir, '.owner'), MARKER, { flag: 'wx', mode: 0o600 })
        marked = true
    } finally {
        if (!marked) rmSync(dir, { recursive: true })
    }
    const isOwned = () =>
        path.dirname(dir) === parent &&
        path.basename(dir).startsWith(PREFIX) &&
        !lstatSync(dir).isSymbolicLink() &&
        lstatSync(dir).isDirectory() &&
        !lstatSync(path.join(dir, '.owner')).isSymbolicLink() &&
        readFileSync(path.join(dir, '.owner'), 'utf8') === MARKER
    return {
        path: dir,
        freeBytes: () => freeBytes(dir),
        cleanup: () => {
            if (!isOwned()) throw new Error('Refusing to remove unowned Flind E2E scratch directory')
            rmSync(dir, { recursive: true })
        },
    }
}
