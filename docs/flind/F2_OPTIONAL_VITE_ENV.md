# Flind F2 — fail-closed configuration outside the Vite environment

Flind's first-party public link registry is consumed not only by the
regular Vite frontend, but also by shared toast/support and standalone
bundles. Other shared Flind modules load region configuration, OAuth client
IDs, marketing referrer host and an incident-status host.

In a bundler that supplies `import.meta` but **not**
`import.meta.env`, unguarded `import.meta.env.VITE_...` reads throw at
module evaluation time, even when a feature is supposed to be disabled.

This patch changes thirteen first-party configuration reads across five
shared frontend modules to `import.meta.env?.VITE_FLIND_...`.

- Vite builds with a configured `import.meta.env` retain their existing
  values and behavior.
- When the environment object is absent, values become undefined and the
  existing Flind validators or empty defaults **fail closed**. No inherited
  domains, OAuth client IDs, telemetry, or status endpoints are invented.
- The public-link and OAuth region approval checks remain unchanged.
- Standalone desktop applications have separate bundler configurations and
  are outside this focused change.

## Validation boundary

- Source regressions in `tools/flind/test_optional_vite_env.py` assert
  that shared modules do not dereference an unavailable environment.
- Full frontend esbuild/Vite/Webpack, Jest, browser, OAuth and desktop
  runtime tests were **not run** due to unavailable connected-device
  execution quota. Guarding a missing `env` object does not by itself
  guarantee every bundler supports `import.meta` syntax.
- CI remains disabled and release is **NO-GO**. Do not publish.
