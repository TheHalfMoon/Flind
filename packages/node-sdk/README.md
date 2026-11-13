# @flind/node

Private, in-repository Flind Node SDK compatibility package, staged from the published `posthog-node` 5.63.2 release.

**Not for publication.** The pinned `@posthog/core` runtime dependency has been replaced in this staged private SDK by the source- and distribution-identical `@flind/core@1.64.1` package, preserving exported symbol ABI. `@flind/core` now uses the private in-repository `@flind/types` package for TypeScript declarations; public compatibility symbols remain temporarily unchanged. Legal attribution remains in LICENSE, NOTICE.md and `packages/core/NOTICE.md`; this package does not independently qualify every SDK endpoint or protocol.

## Explicit Flind-owned collection host (no silent cloud fallback)

Constructors for the checked-in CJS and ESM builds now require a `host` option. Missing or blank hosts fail **synchronously**, before enqueueing an event or opening a connection. The inherited source-vendor `.posthog.com` and `.posthog.dev` domains are forbidden.

```ts
import { PostHog } from '@flind/node'

const client = new PostHog('synthetic-or-own-project-key', {
  host: 'https://collector.flind.example', // replace with YOUR Flind-operated HTTPS origin
  enableExceptionAutocapture: false,
})
```

The `host` option and any separately supplied `appHost` (for email APIs) must each be a safe HTTPS origin without embedded credentials, URL path, query or fragment. An owned event collector does **not** grant permission to send email API credentials to an unrelated `appHost`. Local, isolated integration tests may explicitly use HTTP with a **numeric loopback address** (`127.0.0.1` or `[::1]`); HTTP remote hosts and `localhost` aliases are rejected. No private Flind cloud collector is provided or operated automatically by this patch. Successful `/batch/` wire parity against synthetic loopback does not prove production deployment or API ownership.

The source and committed `dist/client.js` (CJS) and `dist/client.mjs` (ESM) contain the same default-deny origin validator. Run the exact-head Node 26 wire regression workflow and CJS/ESM smoke checks when changing either form. The SDK is still private, not published, and must not be distributed until the Flind release gates are fully qualified and GREEN LIGHT FLIND is explicitly given.

Read LICENSE and NOTICE.md for exact provenance and license information.
