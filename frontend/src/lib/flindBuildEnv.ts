// Flind's browser configuration, injected at build time by Vite's `define` (see vite.config.mts).
// Kept free of `import.meta` so Node-based tools (Jest, Playwright) can load the modules that read
// it. There, and in any build without these variables, every value is undefined: fail closed.
declare const __FLIND_BUILD_ENV__: Readonly<Record<string, string | undefined>> | undefined

export const flindBuildEnv: Readonly<Record<string, string | undefined>> =
    typeof __FLIND_BUILD_ENV__ !== 'undefined' ? __FLIND_BUILD_ENV__ : {}
