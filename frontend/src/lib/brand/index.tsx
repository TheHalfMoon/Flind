// App-wide Flind identity entrypoint. Visual branding stays under Flind control.
// The type contract is retained until first-party UI packages are fully migrated.
import type { LogoProps, LogomarkProps } from '@posthog/brand/logo'

import { cn } from 'lib/utils/css-classes'

export type LogoSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl'

const LOGO_SIZE_HEIGHTS: Record<LogoSize, number> = {
    xs: 20,
    sm: 24,
    md: 28,
    lg: 32,
    xl: 48,
}

type WithLogoSize<P> = Omit<P, 'size' | 'width' | 'height'> & { size?: LogoSize }
export type AppLogoProps = WithLogoSize<LogoProps>
export type AppLogomarkProps = WithLogoSize<LogomarkProps>

// This text-only mark is a temporary first-party replacement for imported
// artwork; production brand assets still require visual review.
export function Logo({ className, size, layout, ...props }: AppLogoProps): JSX.Element {
    const height = LOGO_SIZE_HEIGHTS[size ?? 'md']
    return (
        <span
            role="img"
            aria-hidden={props['aria-hidden']}
            aria-label={props['aria-hidden'] ? undefined : 'Flind'}
            className={cn('inline-flex items-center whitespace-nowrap font-bold tracking-tight text-current', className)}
            style={{ height, fontSize: Math.round(height * 0.8), lineHeight: 1 }}
        >
            {layout === 'logomark' ? 'F' : 'Flind'}
        </span>
    )
}

export function Logomark({ className, size }: AppLogomarkProps): JSX.Element {
    const height = LOGO_SIZE_HEIGHTS[size ?? 'md']
    return (
        <span
            role="img"
            aria-label="Flind"
            className={cn('inline-flex shrink-0 items-center justify-center rounded-md border border-current font-bold text-current', className)}
            style={{ height, width: height, fontSize: Math.round(height * 0.6), lineHeight: 1 }}
        >
            F
        </span>
    )
}
