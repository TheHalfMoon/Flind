import type { SourceMapsPlatform } from './types'

// Descriptive labels only. Upload commands must be specific to the owner's Flind deployment.
export const SOURCE_MAPS_PLATFORM_LABELS: Record<
    SourceMapsPlatform,
    { platform: string; symbols: string; symbol: string }
> = {
    javascript: { platform: 'JavaScript', symbols: 'source maps', symbol: 'source map' },
    java: { platform: 'Android', symbols: 'mapping files', symbol: 'mapping file' },
    native: { platform: 'iOS and native', symbols: 'debug symbols', symbol: 'debug symbols' },
}
