# @flind/icons

Flind's React icon set: a vendored copy of the published upstream icon build (0.39.0), with `IconLogomark` replaced by
Flind's mark. See `NOTICE.md` for provenance and licensing.

```tsx
import { IconLogomark } from '@flind/icons'

const Example = (): JSX.Element => <IconLogomark className="size-4" />
```

Icons are React components that render an `<svg>`. They accept SVG props and a `ref`, fill with `currentColor`, and
take the `LemonIcon` class plus any `className` you pass.

This is a private workspace package; there is no build step. `dist/` is the upstream build and must not be edited.
Flind changes go in `index.mjs`, `index.cjs` and `index.d.ts`.
