// @flind/icons types: everything from the vendored upstream icon build (v0.39.0), with IconLogomark
// redeclared for Flind's mark (same props as upstream). A local export takes precedence over `export *`.
import type { IconComponent, IconProps } from './dist/src/types/icon-types'

export * from './dist/index'

export declare const IconLogomark: IconComponent<IconProps>
