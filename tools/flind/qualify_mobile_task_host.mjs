import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const read = (path) => readFileSync(new URL('../../' + path, import.meta.url), 'utf8')

test('mobile Tasks runtime cannot default to an inherited upstream project', () => {
    const routing = read('products/mobile/src/features/chat/ChatEntryScreen.tsx')
    const selection = read('products/mobile/src/features/chat/taskRuntimeSelection.ts')
    assert.doesNotMatch(routing, /scope\.host === 'https:\/\/us\.posthog\.com'/)
    assert.match(routing, /isTasksRuntimeProject\(scope\)/)
    assert.match(selection, /EXPO_PUBLIC_FLIND_TASKS_HOST/)
    assert.match(selection, /EXPO_PUBLIC_FLIND_TASKS_PROJECT_ID/)
    assert.match(selection, /isInheritedProviderHostname\(url\.hostname\)/)
    assert.match(selection, /host\.origin === origin/)
    assert.match(selection, /scope\.projectId !== projectId/)
})
