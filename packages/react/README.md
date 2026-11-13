# @flind/react

Flind's in-repository React SDK compatibility package. Vendored from the MIT-licensed React integration published at version 1.11.3; see NOTICE.md and LICENSE.

This is **not published**. The original public React API symbol names (such as `PostHogErrorBoundary`) and the `posthog-js` peer dependency are retained temporarily for source/binary compatibility. This does **not** make the underlying browser SDK Flind-native or its data ingestion independently qualified. Migrate code symbols and the browser SDK together in a later tested stage.

Entry points: ESM `dist/esm/index.js`, CommonJS `dist/umd/index.js`, types `dist/types/index.d.ts`, and `slim` / `surveys` subpath directories. Do not ship or publish without complete SDK security, privacy and ingestion tests.

## Flind-owned React analytics initialization

The full `PostHogProvider` compatibility API supports both `client` and
`apiKey` modes. In `apiKey` mode, Flind **requires an explicitly configured
collector origin**; it never falls back to the source provider's SaaS.

```tsx
<PostHogProvider
    apiKey="your-flind-project-key"
    options={{ api_host: 'https://collector.flind.example' }}
>
    <YourApp />
</PostHogProvider>
```

Replace the example domain with an operator-controlled HTTPS collector.
A missing `api_host`, any inherited `posthog.com`/`posthog.dev` endpoint,
a non-HTTPS remote URL, or URL credentials/path/query will prevent automatic
initialization. An optional `ui_host` must meet the same requirements; when
not provided it is derived from the validated collector origin. Explicit HTTP
is allowed only for numeric loopback addresses in local synthetic QA.

When previously initialized analytics options are changed to an unsafe host,
the provider calls `opt_out_capturing()` rather than reconfiguring the
client to that destination. Callers who pass a preinitialized `client`
remain responsible for the privacy and network configuration of that client:
the provider does not control or validate its prior network traffic.

The checked-in full ESM/UMD runtime files and TypeScript source are guarded
together. The slim and surveys entrypoints are unchanged. The `posthog-js`
peer dependency and original public API names remain temporarily for
compatibility, with licenses and provenance in LICENSE/NOTICE.md.

**Release NO-GO:** This is a narrow provider boundary, not an independent
browser SDK or proof of operational Flind cloud ingestion, consent compliance,
all SDK network egress isolation or ownership of arbitrary domains. Do not
publish a package or distribute an application until dedicated end-to-end
evidence and explicit GREEN LIGHT FLIND.
