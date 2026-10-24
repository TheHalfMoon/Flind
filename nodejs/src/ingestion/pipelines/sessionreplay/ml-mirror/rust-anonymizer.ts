type RustAnonymizer = typeof import('@flind/replay-anonymizer')

let rustAnonymizer: RustAnonymizer | undefined

// Lazily loaded so deployments that never run the mirror don't pay the native-module load (and so a
// missing addon only breaks the native path, not every import of this module).
export function getRustAnonymizer(): RustAnonymizer {
    if (!rustAnonymizer) {
        rustAnonymizer = require('@flind/replay-anonymizer') as RustAnonymizer
    }
    return rustAnonymizer
}
