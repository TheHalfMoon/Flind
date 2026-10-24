# F3 Wave 15 — safe service/utility npm identity migration

## Scope

Migrate the names and exact internal references for seven first-party
workspace packages to the Flind npm scope:

- ML image scrubber sidecar
- Canvas builder package
- Visual review CLI
- Agent proxy service
- Credentials service
- OAuth/auth proxy
- Stripe integration service

All seven manifests are now explicitly `private: true`. The existing source
logic, network configuration, database schemas, OAuth contracts, payment
behavior, SDK exports and packaging paths are intentionally unchanged.

## Specific compatibility boundary

The repository consumes a **published third-party** package
`@posthog/mcp@0.23.0` as an external dependency of the MCP analytics
integration. Its published name, lockfile integrity and dependency metadata
must NOT be automatically relabeled as `@flind/mcp`. This wave deliberately
does not rename `services/mcp` or published client SDKs or desktop apps:
those require a dedicated compatibility check and first-party builds.

## Test evidence

- Workspace graph must preserve at least **261** internal workspace dependency
  edges with zero unresolved.
- Flind-scoped internal package IDs increase **132 → 139**.
- Inherited-scoped first-party workspace IDs decrease **27 → 20**.
- Five new Python source regressions verify manifest identity/privacy,
  dependency graph, absence of inherited exact imports, published MCP
  registry protection and lockfile safety.
- Frozen `pnpm --lockfile-only --offline --frozen-lockfile` check under
  Node 24 with original supply-chain trust policy is required before merge.
- Full Flind Python source suite and basic entrypoint checks remain required.

## Remaining release gates

The rename does not prove production builds, OAuth/Stripe operation,
first-party proxy DNS reachability, actual network data boundaries, published
SDK package compatibility, frontend/Jest, Django/DB or cross-platform
packaging. An unverified package ID must not be represented as a published
release. Keep Flind private, GitHub Actions disabled, no deployment.
**Release NO-GO.**
