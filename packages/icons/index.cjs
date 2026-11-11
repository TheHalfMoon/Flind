'use strict'
// @flind/icons CommonJS entry: the vendored upstream icon build (v0.39.0), with IconLogomark replaced by
// Flind's mark. Keep the drawing in sync with index.mjs. See NOTICE.md.
const { createElement, forwardRef } = require('react')

const upstream = require('./dist/posthog-icons.cjs.js')

// Flind's mark from frontend/public/flind-icon.svg (64x64 tile, "F", accent dot), drawn in one colour:
// the tile is filled with currentColor and the "F" and dot are knocked out (evenodd).
const FLIND_LOGOMARK_PATH =
    'M15 0H49A15 15 0 0 1 64 15V49A15 15 0 0 1 49 64H15A15 15 0 0 1 0 49V15A15 15 0 0 1 15 0Z' +
    'M19 16H46V25H28V31H41V39H28V49H19Z' +
    'M42 44A4 4 0 1 0 50 44A4 4 0 1 0 42 44Z'

// Mirrors upstream's BaseIcon: LemonIcon class, width 100%, fill currentColor; caller props win.
const IconLogomark = forwardRef(function IconLogomark({ className, ...props }, ref) {
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

module.exports = { ...upstream, IconLogomark }
