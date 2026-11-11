// @flind/icons ESM entry: the vendored upstream icon build (v0.39.0), with IconLogomark replaced by
// Flind's mark. A local export takes precedence over the same name from `export *`. See NOTICE.md.
import { createElement, forwardRef } from 'react'

export * from './dist/posthog-icons.es.js'

// Flind's mark from frontend/public/flind-icon.svg (64x64 tile, "F", accent dot), drawn in one colour:
// the tile is filled with currentColor and the "F" and dot are knocked out (evenodd).
const FLIND_LOGOMARK_PATH =
    'M15 0H49A15 15 0 0 1 64 15V49A15 15 0 0 1 49 64H15A15 15 0 0 1 0 49V15A15 15 0 0 1 15 0Z' +
    'M19 16H46V25H28V31H41V39H28V49H19Z' +
    'M42 44A4 4 0 1 0 50 44A4 4 0 1 0 42 44Z'

// Mirrors upstream's BaseIcon: LemonIcon class, width 100%, fill currentColor; caller props win.
export const IconLogomark = /* @__PURE__ */ forwardRef(function IconLogomark({ className, ...props }, ref) {
    return createElement(
        'svg',
        {
            ref,
            className: 'LemonIcon' + (className ? ` ${className}` : ''),
            width: '100%',
            fill: 'currentColor',
            xmlns: 'http://www.w3.org/2000/svg',
            viewBox: '0 0 64 64',
            ...props,
        },
        createElement('path', { fillRule: 'evenodd', clipRule: 'evenodd', d: FLIND_LOGOMARK_PATH })
    )
})
