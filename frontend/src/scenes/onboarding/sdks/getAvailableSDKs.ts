import { isOwnedFlindDocsDestination } from 'lib/flindPublicLinks'
import { isKeyOf } from 'lib/utils/guards'

import { SDK, SDKDocsLinkOverrides, SDKInstructionsMap, SDKTag, SDKTagOverrides } from '~/types'

import { ALL_SDKS } from './allSDKs'

export const getAvailableSDKs = (
    availableSDKInstructionsMap: SDKInstructionsMap,
    sdkTagOverrides: SDKTagOverrides,
    sdkDocsLinkOverrides: SDKDocsLinkOverrides
): SDK[] => {
    const availableSDKKeys = Object.keys(availableSDKInstructionsMap)
    return ALL_SDKS.filter((sdk) => availableSDKKeys.includes(sdk.key)).map((sdk) => {
        const rawDocsOverride = isKeyOf(sdk.key, sdkDocsLinkOverrides) ? sdkDocsLinkOverrides[sdk.key] : undefined
        return {
            ...sdk,
            ...(isKeyOf(sdk.key, sdkTagOverrides) ? { tags: sdkTagOverrides[sdk.key] as SDKTag[] } : {}),
            ...(rawDocsOverride !== undefined
                ? { docsLink: isOwnedFlindDocsDestination(rawDocsOverride) ? rawDocsOverride : '' }
                : {}),
        }
    })
}
