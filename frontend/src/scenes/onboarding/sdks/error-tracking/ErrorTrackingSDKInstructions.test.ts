import { flindDocsUrl } from 'lib/flindPublicLinks'

import { SDKKey } from '~/types'

import { ALL_SDKS } from '../allSDKs'
import { getAvailableSDKs } from '../getAvailableSDKs'
import { ErrorTrackingSDKDocsLinkOverrides, ErrorTrackingSDKInstructions } from './ErrorTrackingSDKInstructions'

describe('ErrorTrackingSDKInstructions', () => {
    const newlySupportedSDKs: Array<[SDKKey, string]> = [
        [SDKKey.RUST, flindDocsUrl('error-tracking/installation/rust') ?? ''],
        [SDKKey.UNITY, flindDocsUrl('error-tracking/installation/unity') ?? ''],
        [SDKKey.ROBLOX, flindDocsUrl('error-tracking/installation/roblox') ?? ''],
        [SDKKey.JAVA, flindDocsUrl('libraries/java') ?? ''],
        [SDKKey.KMP, flindDocsUrl('libraries/kmp') ?? ''],
        [SDKKey.CONVEX, flindDocsUrl('libraries/convex') ?? ''],
    ]

    it.each(newlySupportedSDKs)('makes %s selectable with working instructions and docs', (sdkKey, docsLink) => {
        const availableSDKs = getAvailableSDKs(ErrorTrackingSDKInstructions, {}, ErrorTrackingSDKDocsLinkOverrides)
        const sdk = availableSDKs.find(({ key }) => key === sdkKey)

        expect(ErrorTrackingSDKInstructions[sdkKey]).not.toBeUndefined()
        expect(sdk).toMatchObject({ key: sdkKey, docsLink })
    })

    it('keeps the AI observability link in shared Convex metadata', () => {
        expect(ALL_SDKS.find(({ key }) => key === SDKKey.CONVEX)?.docsLink).toBe(
            flindDocsUrl('ai-observability/installation/convex') ?? ''
        )
    })
})
