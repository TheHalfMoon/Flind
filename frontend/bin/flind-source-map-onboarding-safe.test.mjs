import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(new URL('../src/scenes/onboarding/error-tracking/OnboardingErrorTrackingSourceMapsStep.tsx', import.meta.url), 'utf8')
const stepLogic = readFileSync(new URL('../src/scenes/onboarding/error-tracking/source-maps/sourceMapsStepLogic.ts', import.meta.url), 'utf8')

test('source-map onboarding never offers an unowned installer, login or symbol upload command', () => {
    assert.doesNotMatch(source, /download\.posthog\.com|releases\.posthog\.com|us\.posthog\.com/)
    assert.doesNotMatch(source, /posthog-cli|@posthog\/cli|curl\s+--proto|curl\s+-LsSf/)
    assert.doesNotMatch(source, /<CodeSnippet|SourceMapsInstructionsModal|automatedSourceMapsTechnologies/)
    assert.match(source, /Installer,\s+authentication and upload commands are intentionally withheld/)
})

test('optional safe setup alternatives remain selectable and skippable', () => {
    assert.match(source, /optionKey="no-minification"/)
    assert.match(source, /optionKey="public-source-maps"/)
    assert.match(source, /optionKey="cli"/)
    assert.match(source, /showSkip=\{!shouldShowContinue\}/)
    assert.match(source, /shouldShowSourceMapStatus && <SourceMapStatus \/>/)
    assert.match(stepLogic, /selectedOption === 'public-source-maps'/)
    assert.match(stepLogic, /selectedOption === 'no-minification'/)
})

test('private source maps and iOS dSYM remain explicitly gated on owned CLI qualification', () => {
    assert.match(source, /Private source maps \(Flind CLI not yet available\)/)
    assert.match(source, /Automatic source-map and iOS dSYM uploads are also unavailable/)
    assert.match(source, /owned-host, authorization, binary integrity and distribution checks/)
    assert.match(source, /Do not install another/)
})
