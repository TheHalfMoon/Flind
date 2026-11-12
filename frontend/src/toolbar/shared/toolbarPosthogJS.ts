import posthog from 'posthog-js'
import { useEffect, useState } from 'react'

import { FeatureFlagKey } from 'lib/constants'

// The toolbar is also imported on arbitrary customer pages and in the extension.
// Never send their diagnostic events or flag requests to a donor-hosted project.
// Only the Flind app itself can opt in using its own server-rendered project key.
const runningOnFlind = !!window.POSTHOG_APP_CONTEXT && !!window.JS_POSTHOG_API_KEY
const apiKey = runningOnFlind ? window.JS_POSTHOG_API_KEY : 'flind_toolbar_disabled'
const apiHost = runningOnFlind ? window.JS_POSTHOG_HOST || window.location.origin : window.location.origin
const telemetryDisabled = !runningOnFlind
// Manifest V3 forbids remote code in an extension, and the browser stores reject it.
const runningInBrowserExtension = !!(globalThis as { chrome?: { runtime?: { id?: string } } }).chrome?.runtime?.id

const initResult = posthog.init(
    apiKey || 'flind_toolbar_disabled',
    {
        api_host: apiHost,
        // Extension and customer-page contexts have no Flind telemetry project.
        // Even if a caller opts in later, before_send drops the event locally.
        opt_out_capturing_by_default: true,
        before_send: telemetryDisabled ? () => null : undefined,
        advanced_disable_decide: telemetryDisabled,
        advanced_disable_feature_flags: telemetryDisabled,
        persistence: 'memory', // We don't want to persist anything, all events are in-memory
        persistence_name: apiKey + '_toolbar', // We don't need this but it ensures we don't accidentally mess with the standard persistence
        bootstrap: {
            featureFlags: {},
        },
        // The web app imports toolbar modules, which creates this instance on every app page load.
        // Only a mounted toolbar reads these flags, so the toolbar loads them and starts the refresh when it mounts.
        advanced_disable_feature_flags_on_first_load: true,
        remote_config_refresh_interval_ms: 0,
        autocapture: false,
        // The toolbar runs on customer pages and must not install global exception handlers.
        capture_exceptions: false,
        capture_pageview: false,
        capture_pageleave: false,
        disable_surveys: true,
        disable_scroll_properties: true,
        disable_product_tours: true,
        disable_session_recording: true,
        disable_external_dependency_loading: runningInBrowserExtension || telemetryDisabled,
        session_recording: {
            // we want to capture the toolbar (which is marked with ph-no-capture
            // so customer sessions don't see it), but also respect the customer's
            // ph-no-capture marks
            blockClass: 'ph-internal-no-capture',
            blockSelector: '.ph-no-capture:not(#__POSTHOG_TOOLBAR__):not(#__POSTHOG_TOOLBAR__ *)',
            maskAllInputs: true,
        },
    },
    'ph_toolbar_internal'
)
if (!initResult) {
    throw new Error('Failed to initialize Flind toolbar instance')
}
export const toolbarPosthogJS = initResult

if (runningOnFlind && window.JS_POSTHOG_SELF_CAPTURE) {
    toolbarPosthogJS.debug()
}

/** Capture an exception with a required toolbar context tag for filtering. */
export function captureToolbarException(
    error: unknown,
    context: string,
    additionalProperties?: Record<string, unknown>
): void {
    toolbarPosthogJS.captureException(error, {
        toolbar_context: context,
        ...additionalProperties,
    })
}

export const useToolbarFeatureFlag = (flag: FeatureFlagKey, match?: string): boolean => {
    const [flagValue, setFlagValue] = useState<boolean | string | undefined>(toolbarPosthogJS.getFeatureFlag(flag))

    useEffect(() => {
        return toolbarPosthogJS.onFeatureFlags(() => setFlagValue(toolbarPosthogJS.getFeatureFlag(flag)))
    }, [flag, match])

    if (match) {
        return flagValue === match
    }

    return !!flagValue
}
