import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const read = (name) => readFileSync(new URL('../../' + name, import.meta.url), 'utf8')

test('Flind mobile legal destinations cannot silently point at inherited provider policies', () => {
    const links = read('products/mobile/src/lib/legalLinks.ts')
    assert.doesNotMatch(links, /https:\/\/posthog\.com\/(?:privacy|terms|docs\/support-options)/)
    assert.match(links, /EXPO_PUBLIC_FLIND_PRIVACY_URL/)
    assert.match(links, /EXPO_PUBLIC_FLIND_TERMS_URL/)
    assert.match(links, /EXPO_PUBLIC_FLIND_SUPPORT_URL/)
    assert.match(links, /isInheritedProviderHostname\(parsed\.hostname\)/)
    assert.match(links, /parsed\.protocol !== 'https:'/)
    assert.match(links, /if \(url === null\) return/)
})

test('unconfigured sign-in and settings do not present active, deceptive policies', () => {
    const settings = read('products/mobile/src/features/settings/LegalGroup.tsx')
    const login = read('products/mobile/src/auth/SignInScreen.tsx')
    assert.match(settings, /\{PRIVACY_POLICY_URL \? \(/)
    assert.match(settings, /\{TERMS_URL \? \(/)
    assert.match(settings, /\{SUPPORT_URL \? \(/)
    assert.match(login, /\{PRIVACY_POLICY_URL \|\| TERMS_URL \? \(/)
    assert.match(login, /\{PRIVACY_POLICY_URL && TERMS_URL \? \(/)
})

test('AI consent cannot proceed without a configured Flind-owned privacy policy', () => {
    const gate = read('products/mobile/src/features/chat/ChatAccessGate.tsx')
    const approval = read('products/mobile/src/features/ai/AiApprovalDialog.tsx')
    const sheet = read('products/mobile/src/features/chat/AiConsentSheet.tsx')
    const aiAccess = read('products/mobile/src/features/chat/aiAccess.ts')
    assert.doesNotMatch(aiAccess, /https:\/\/posthog\.com\/privacy/)
    assert.match(gate, /PRIVACY_POLICY_URL \? \(\) => openLegalLink/)
    assert.match(approval, /PRIVACY_POLICY_URL\s+\? \(\) => openLegalLink/)
    assert.match(sheet, /disabled=\{pending \|\| !onOpenPrivacyPolicy\}/)
    assert.match(sheet, /chat-ai-policy-unconfigured/)
    assert.match(sheet, /\{onOpenPrivacyPolicy \? \(/)
})
