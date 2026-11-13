# Node onboarding: correct transitional SDK constructor

## Problem

The install command in the Flind Node SDK onboarding screen points to
the public compatibility package `posthog-node`, but the corresponding
JavaScript snippet imported a non-existent named class `Flind` from that
package. A user copying the install and setup instructions would fail
at import or constructor initialization before making any event request.

The installed compatibility package exports `PostHog` (according to
its public Node SDK documentation), not `Flind`. That name is an SDK
implementation class, **not** the Flind application's brand.

Reference: https://posthog.com/docs/libraries/node/reference

## Repair

- Use `import { PostHog } from 'posthog-node'` and
  `const client = new PostHog(...)` with the existing explicit first-party
  `host: apiHostOrigin()` configured for the current Flind instance.
- Show `YOUR_PROJECT_API_KEY` instead of the string `undefined` when
  the currently selected team/token has not loaded yet.
- Include a reminder to await `client.shutdown()` before process exit
  so queued analytics events have an opportunity to flush.
- Preserve optional exception autocapture and existing install managers.

This does **not** publish `@flind/node`; that private owned package is
staged separately and must pass the full package/ingestion/release
qualification before it replaces the temporary compatibility package.
Do not claim the donor client is a Flind-owned public release.

## Verification

`frontend/bin/flind-node-onboarding-contract.test.mjs` checks the
matching installed package and imported class, rejects the broken
constructor, requires an explicit Flind app-origin host, disallows
inherited donor cloud defaults and preserves the optional settings.
Run branch-scoped full frontend Jest/TypeScript checks in addition to
this source contract and the rename ratchet.

It does not prove a successful Node-to-Rust-Capture-to-ClickHouse event.
That remains separately gated by the opt-in full-service Playwright run
in PR #68. Do not distribute any public Flind package, tag, release or
deployment without explicit `GREEN LIGHT FLIND`.
