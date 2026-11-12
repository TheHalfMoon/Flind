import { existsSync } from 'node:fs'
import { join } from 'node:path'

import type { ConfigContext, ExpoConfig } from 'expo/config'

import variantTable from './src/lib/appVariants.json'

// There is no inherited Expo account, project, update feed, or store submission target.
const expoOwner = process.env.FLIND_EXPO_OWNER?.trim() ?? ''
const expoProjectId = process.env.FLIND_EXPO_PROJECT_ID?.trim() ?? ''

function verifyPublishingIdentity(): void {
    if ((expoOwner === '') !== (expoProjectId === '')) {
        throw new Error('FLIND_EXPO_OWNER and FLIND_EXPO_PROJECT_ID must be configured together.')
    }
    if (expoOwner.toLowerCase() === 'posthog' || expoOwner.toLowerCase() === 'posthog-inc') {
        throw new Error('Use an Expo account controlled by Flind, not the original application owner.')
    }
    if (expoProjectId && !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(expoProjectId)) {
        throw new Error('FLIND_EXPO_PROJECT_ID must be a real Expo project UUID.')
    }
}

// Mobile deep-link claims must only name Flind-owned, HTTPS origins. Unconfigured
// cloud environments do not register upstream associated domains.
function configuredAppLinkHosts(): string[] {
    const result: string[] = []
    for (const name of ['EXPO_PUBLIC_FLIND_US_HOST', 'EXPO_PUBLIC_FLIND_EU_HOST']) {
        const raw = process.env[name]?.trim()
        if (!raw) continue
        let parsed: URL
        try {
            parsed = new URL(raw)
        } catch {
            throw new Error(name + ' must be an absolute HTTPS origin.')
        }
        const host = parsed.hostname.toLowerCase()
        if (parsed.protocol !== 'https:' || parsed.port || parsed.username || parsed.password ||
            (parsed.pathname !== '/' && parsed.pathname !== '') || parsed.search || parsed.hash ||
            host === 'posthog.com' || host.endsWith('.posthog.com') ||
            host === 'posthog.dev' || host.endsWith('.posthog.dev')) {
            throw new Error(name + ' must identify a Flind-owned HTTPS origin, without a path or credentials.')
        }
        result.push(host)
    }
    return [...new Set(result)]
}

type AppVariant = keyof typeof variantTable.variants

function isAppVariant(value: string): value is AppVariant {
    return Object.hasOwn(variantTable.variants, value)
}

// eas.json sets APP_VARIANT per build profile, and the update scripts in package.json set it per channel.
// A plain local run has none and gets the store identity; the app still treats a Metro bundle as development.
function readVariant(): AppVariant {
    const value = process.env.APP_VARIANT
    if (value === undefined || value === '') {
        return 'production'
    }
    if (!isAppVariant(value)) {
        throw new Error(`APP_VARIANT must be development, preview or production, not "${value}".`)
    }
    return value
}

// On EAS, GOOGLE_SERVICES_JSON is a file environment variable: the build gets the path of the uploaded file.
// Locally, a google-services.json next to this file is used when it exists. git and EAS both ignore it.
function googleServicesFile(projectRoot: string): string | undefined {
    if (process.env.GOOGLE_SERVICES_JSON) {
        return process.env.GOOGLE_SERVICES_JSON
    }
    return existsSync(join(projectRoot, 'google-services.json')) ? './google-services.json' : undefined
}

const ICONS: Record<AppVariant, { png: string; adaptive: string; ios: string }> = {
    development: {
        png: './assets/icon-dev.png',
        adaptive: './assets/adaptive-icon-dev.png',
        ios: './assets/app-dev.icon',
    },
    preview: {
        png: './assets/icon-preview.png',
        adaptive: './assets/adaptive-icon-preview.png',
        ios: './assets/app-preview.icon',
    },
    production: { png: './assets/icon.png', adaptive: './assets/adaptive-icon.png', ios: './assets/app.icon' },
}



export default ({ config, projectRoot }: ConfigContext): ExpoConfig => {
    verifyPublishingIdentity()
    const appLinkHosts = configuredAppLinkHosts()
    const variant = readVariant()
    const { name, idSuffix, scheme } = variantTable.variants[variant]
    const appId = `${variantTable.productionAppIds.ios}${idSuffix}`
    const androidPackage = `${variantTable.productionAppIds.android}${idSuffix}`
    // The HedgehogWidget target and both Swift readers of the shared store derive the same name from the bundle id.
    const appGroup = `group.${appId}`
    const icons = ICONS[variant]

    return {
        ...config,
        name,
        slug: 'flind',
        ...(expoOwner ? { owner: expoOwner } : {}),
        scheme,
        version: '1.13.0',
        orientation: 'default',
        userInterfaceStyle: 'automatic',
        icon: icons.png,
        ios: {
            icon: icons.ios,
            bundleIdentifier: appId,
            // The server lists the matching paths in posthog/mobile_app_links.py.
            associatedDomains: appLinkHosts.map((host) => `applinks:${host}`),
            // Local device builds sign automatically with this team; EAS builds carry their own credentials.
            appleTeamId: process.env.APPLE_TEAM_ID,
            supportsTablet: false,
            entitlements: {
                // Shared with the HedgehogWidget extension, which reads the choreography the app writes.
                'com.apple.security.application-groups': [appGroup],
            },
            infoPlist: {
                ITSAppUsesNonExemptEncryption: false,
                'com.posthog.posthog.CAPTURE_PUSH_NOTIFICATION_OPENED': false,
            },
            // Expo merges these into the template's manifest, which already declares the reasons React Native needs.
            privacyManifests: {
                NSPrivacyTracking: false,
                NSPrivacyAccessedAPITypes: [
                    {
                        NSPrivacyAccessedAPIType: 'NSPrivacyAccessedAPICategoryUserDefaults',
                        // 1C8F.1 covers the App Group suite that the widget sync writes.
                        NSPrivacyAccessedAPITypeReasons: ['CA92.1', '1C8F.1'],
                    },
                    {
                        NSPrivacyAccessedAPIType: 'NSPrivacyAccessedAPICategoryFileTimestamp',
                        NSPrivacyAccessedAPITypeReasons: ['C617.1'],
                    },
                    {
                        NSPrivacyAccessedAPIType: 'NSPrivacyAccessedAPICategorySystemBootTime',
                        NSPrivacyAccessedAPITypeReasons: ['35F9.1'],
                    },
                ],
                NSPrivacyCollectedDataTypes: [
                    collected('NSPrivacyCollectedDataTypeUserID', ['AppFunctionality', 'Analytics']),
                    collected('NSPrivacyCollectedDataTypeDeviceID', ['AppFunctionality', 'Analytics']),
                    collected('NSPrivacyCollectedDataTypeProductInteraction', ['Analytics']),
                    collected('NSPrivacyCollectedDataTypeEmailAddress', ['AppFunctionality']),
                    collected('NSPrivacyCollectedDataTypeName', ['AppFunctionality']),
                    // Flind derives a coarse location from the request IP of each analytics event.
                    collected('NSPrivacyCollectedDataTypeCoarseLocation', ['Analytics']),
                    // Chat messages the user sends to Flind AI.
                    collected('NSPrivacyCollectedDataTypeOtherUserContent', ['AppFunctionality']),
                    // Photos the user attaches to a Flind AI chat.
                    collected('NSPrivacyCollectedDataTypePhotosorVideos', ['AppFunctionality']),
                ],
            },
        },
        android: {
            package: androidPackage,
            // Keep pathPattern in sync with APP_LINK_PATHS in posthog/mobile_app_links.py. A pathPattern cannot
            // exclude a path, so it requires the hyphen of a report UUID. That keeps the web-only
            // `/inbox/reports/triage` (APP_LINK_EXCLUDED_PATHS) in the browser.
            intentFilters: [
                {
                    action: 'VIEW',
                    autoVerify: true,
                    data: appLinkHosts.map((host) => ({
                        scheme: 'https',
                        host,
                        pathPattern: '/project/.*/inbox/reports/.*-.*',
                    })),
                    category: ['BROWSABLE', 'DEFAULT'],
                },
            ],
            googleServicesFile: googleServicesFile(projectRoot),
            adaptiveIcon: {
                foregroundImage: icons.adaptive,
                backgroundColor: '#FFFFFF',
            },
        },
        web: {
            favicon: './assets/favicon.png',
            bundler: 'metro',
        },
        plugins: [
            'expo-router',
            ['expo-secure-store', { configureAndroidBackup: false }],
            './plugins/withAndroidChartWidgetBackup',
            'expo-notifications',
            'expo-web-browser',
            [
                'expo-splash-screen',
                {
                    image: './assets/splash-icon.png',
                    imageWidth: 120,
                    resizeMode: 'contain',
                    backgroundColor: '#F6F6F3',
                    dark: {
                        image: './assets/splash-icon-dark.png',
                        backgroundColor: '#1D1F27',
                    },
                },
            ],
            'expo-font',
            'expo-updates',
            [
                'expo-image-picker',
                {
                    photosPermission: 'Flind opens your photo library so you can attach images to Flind AI chats.',
                    // The composer attaches from the library only.
                    cameraPermission: false,
                    microphonePermission: false,
                },
            ],
            ['expo-video', { supportsBackgroundPlayback: false, supportsPictureInPicture: true }],
            ['./plugins/withAndroidLoopbackNetworking', { allowLoopback: variant !== 'production' }],
            './plugins/withAndroidAdaptiveIconInsets',
            './plugins/withAndroidNotificationIntents',
            '@bacons/apple-targets',
            './plugins/withIosArchiveScheme',
        ],
        // Until an independent Flind OTA signing and publishing flow is reviewed,
        // no mobile variant may fetch an inherited Expo update bundle.
        updates: { enabled: false },
        runtimeVersion: {
            policy: 'appVersion',
        },
        extra: {
            router: {},
            appVariant: variant,
            ...(expoProjectId ? { eas: { projectId: expoProjectId } } : {}),
        },
    }
}

type CollectionPurpose = 'AppFunctionality' | 'Analytics'

function collected(
    type: string,
    purposes: CollectionPurpose[]
): {
    NSPrivacyCollectedDataType: string
    NSPrivacyCollectedDataTypeLinked: boolean
    NSPrivacyCollectedDataTypeTracking: boolean
    NSPrivacyCollectedDataTypePurposes: string[]
} {
    return {
        NSPrivacyCollectedDataType: type,
        NSPrivacyCollectedDataTypeLinked: true,
        NSPrivacyCollectedDataTypeTracking: false,
        NSPrivacyCollectedDataTypePurposes: purposes.map((purpose) => `NSPrivacyCollectedDataTypePurpose${purpose}`),
    }
}
