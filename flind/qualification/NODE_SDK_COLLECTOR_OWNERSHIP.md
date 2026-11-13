# Flind private Node SDK default-deny collector qualification

## Scope

The staged `@flind/node` SDK retained the copied donor's default collection host `https://us.i.posthog.com` in its TypeScript source **and** its checked-in CJS/ESM runtime files. A copied SDK invoked without `options.host` could therefore send events to a third-party server.

This change ensures construction fails synchronously on missing or unsafe host in source and both committed runtime formats. The sole allowed HTTP origins are explicit numeric loopback IPs for offline synthetic integration tests. HTTPS may point at a Flind operator-controlled origin with no URL credentials, paths or query/fragment. A suffix rejection prevents all inherited `.posthog.com` and `.posthog.dev` hosts, even when explicitly selected.

The standalone Node 26 qualification tests both `require('@flind/node')` and `import('@flind/node')`, preserves the pinned 5.63.2 module export ABI, executes local loopback `/batch/` wire parity and checks that the source and two compiled files cannot reintroduce the copied default.

## Boundaries and NO-GO

The package still contains vendor APIs, `@posthog/core`, copied SDK protocol identifiers and potential domain-specific default behaviors in ancillary endpoints. This change audits only the collector destination at SDK construction. It does **not** automatically qualify email-specific API routing, error tracking, all network transports, package provenance, actual self-hosted Flind ingestion, SDK publication or data privacy compliance. Do not publish a package or release Flind without independent full-stack validation and GREEN LIGHT FLIND.
