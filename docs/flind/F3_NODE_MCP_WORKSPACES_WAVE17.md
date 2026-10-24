# F3 Wave 17 — Node ingestion and MCP internal package identities

## Scope

Migrate the two remaining straightforward internal service npm workspace
package identities:

- `nodejs/package.json`: `@flind/nodejs`
- `services/mcp/package.json`: `@flind/mcp`

Make both internal manifests `private: true`. Update exact internal
Node.js package references and pnpm CLI filters targeting the local MCP
server, without changing runtime ingestion algorithms, published package
versions, SDK APIs, customer credentials, external MCP telemetry libraries,
or database persistence.

## Published-registry collision guarded

The private workspace's former name `@posthog/mcp` collides with a
**published, separately versioned** SDK dependency in the existing lockfile.
The repository still consumes `@posthog/mcp@0.23.0` through its published
`@posthog/mcp-analytics` alias. **Do not rename that published package
or its integrity snapshot.** It is not a Flind-owned build. Source docs
and SDK imports describing this actual provider must remain accurate.

The frontend's `@posthog/lemon-ui@0.0.0` is also an external compiled npm
artifact in the current dependency graph. Its local source manifest is not
included as a published first-party workspace. Changing its import name
without a reproducible first-party UI build would break dependency
installation, so that last inherited-scoped manifest needs a separate
source/build qualification and migration.

## Verification

- 169 tracked manifests, 261 local `workspace:*` dependency edges,
  zero unresolved references.
- First-party Flind package identity count **156 → 158**; one inherited
  source-project package name remains: `@posthog/lemon-ui`.
- Five Python source tests guard private identity, graph completeness,
  first-party MCP CLI filters, original published MCP/UI registry
  snapshots, and Node source references.
- Frozen offline pnpm lockfile-only supply-chain validation under Node 24
  **PASS** with unchanged trust policy.
- Full Flind Python suite and basic entrypoint checks must pass before merge.

## Release limits

No new npm publication was made and no public MCP/Node.js distribution has
been qualified. Built Node service, Django integration, real MCP OAuth,
frontend/desktop builds, database migrations, cross-platform E2E and
outbound network traces remain release blockers. Keep repo private and
inherited GitHub Actions disabled. **NO-GO.**
