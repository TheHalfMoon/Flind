/**
 * @flind/quill — Flind's unified design system.
 *
 * Re-exports the public surface of primitives, components, and blocks as a
 * single package. Consumers should install and import from here rather than
 * the internal sub-packages.
 *
 * Pair this with `import '@flind/quill/styles.css'` once in your app's
 * entry point to load the pre-compiled stylesheet.
 */

export * from '@flind/quill-primitives'
export * from '@flind/quill-components'
export * from '@flind/quill-blocks'
