import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const repo = new URL('../../', import.meta.url)
const files = {
    account: 'frontend/src/lib/components/Account/AccountMenu.tsx',
    agents: 'frontend/src/lib/components/MCPHint/AgentBadgeRotator.tsx',
    frames: 'frontend/src/lib/components/Errors/Frame/CollapsibleFrameHeader.tsx',
    previews: 'frontend/src/lib/components/FeaturePreviews/FeaturePreviews.tsx',
    sql: 'frontend/src/lib/components/HogQLEditor/HogQLEditor.tsx',
}
const source = Object.fromEntries(
    Object.entries(files).map(([key, path]) => [key, readFileSync(new URL(path, repo), 'utf8')])
)

test('five live navigation/help components never send users to inherited PostHog docs or marketing', () => {
    for (const [name, content] of Object.entries(source)) {
        assert.doesNotMatch(content, /https?:\/\/(?:[\w-]+\.)?posthog\.com\b/i, name)
        assert.doesNotMatch(content, /sales@posthog\.com/i, name)
    }
})

test('account releases link is Flind-owned and has an accurate label', () => {
    assert.match(source.account, /to="https:\/\/github\.com\/TheHalfMoon\/Flind\/releases"/)
    assert.match(source.account, /Release notes/)
    assert.match(source.account, /data-attr="whats-new-button"/)
})

test('agent badges are not clickable inherited desktop or community offers', () => {
    assert.doesNotMatch(source.agents, /Flind Desktop|POSTHOG_CODE_URL|POSTHOG_SLACK_URL|agent\.url/)
    assert.doesNotMatch(source.agents, /IconExternal|<Link\b/)
    assert.match(source.agents, /const AGENTS: BadgeAgent\[\]/)
    assert.match(source.agents, /name: 'Claude'/)
    assert.match(source.agents, /inStorybook\(\)/)
})

test('symbolication tooltips explain local availability without suggesting donor uploads', () => {
    assert.doesNotMatch(source.frames, /SYMBOL_SETS_DOC_LINK|docLink=/)
    assert.match(source.frames, /Symbol information is unavailable in this Flind deployment/)
    assert.match(source.frames, /approved source-map or symbol upload process/)
    assert.match(source.frames, /<FrameDropDownMenu/)
})

test('feature preview and SQL help remain local rather than linking to donor docs', () => {
    assert.match(source.previews, /appropriately configured reverse proxy/)
    assert.doesNotMatch(source.previews, /docs\/advanced\/proxy/)
    assert.match(source.sql, /HogQL expressions run on this Flind instance/)
    assert.match(source.sql, /onClick=\{\(\) => onChange\(bufferedValue\)\}/)
})
