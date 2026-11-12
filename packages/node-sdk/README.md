# @flind/node

Private, in-repository Flind Node SDK compatibility package, staged from the published `posthog-node` 5.63.2 release.

**Not for publication.** The `@posthog/core` runtime dependency and inherited public symbol names remain for ABI compatibility. Legal attribution remains in LICENSE and NOTICE.md; this package does not independently qualify every SDK endpoint or protocol.

## Explicit Flind-owned collection host (no silent cloud fallback)

Constructors for the checked-in CJS and ESM builds now require a `host` option. Missing or blank hosts fail **synchronously**, before enqueueing an event or opening a connection. The inherited source-vendor `.posthog.com` and `.posthog.dev` domains are forbidden.

```ts
import { PostHog } from '@flind/node'

const client = new PostHog('synthetic-or-own-project-key', {
  host: 'https://collector.flind.example', // replace with YOUR Flind-operated HTTPS origin
  enableExceptionAutocapture: false,
})
```

The option must be an HTTPS origin without embedded credentials, URL path, query or fragment. Local, isolated integration tests may explicitly use HTTP with a **numeric loopback address** (`127.0.0.1` or `[::1]`); HTTP remote hosts and `localhost` aliases are rejected. No private Flind cloud collector is provided or operated automatically by this patch. Successful `/batch/` wire parity against synthetic loopback does not prove production deployment or API ownership.

The source and committed `dist/client.js` (CJS) and `dist/client.mjs` (ESM) contain the same default-deny origin validator. Run the exact-head Node 26 wire regression workflow and CJS/ESM smoke checks when changing either form. The SDK is still private, not published, and must not be distributed until the Flind release gates are fully qualified and GREEN LIGHT FLIND is explicitly given.

Read LICENSE and NOTICE.md for exact provenance and license information.
