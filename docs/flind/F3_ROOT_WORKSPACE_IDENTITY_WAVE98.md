# Wave 98 — Rename remaining first-party monorepo root package identities

## Change

The Wave 97 graph audit confirmed zero inherited `@posthog/` scoped packages but revealed two unscoped first-party workspace roots that still exposed inherited package identities:

| Root | Old npm name | Flind name |
| --- | --- | --- |
| `packages/agent/package.json` | `posthog-agent-workspace` | `@flind/agent-workspace` |
| `products/desktop/package.json` | `posthog-code` | `@flind/desktop-workspace` |

Their user-facing descriptions now use Flind. The desktop package's marketing keyword `posthog` is now `flind`. **The donor's `author` field and MIT license are intentionally retained** as provenance and required legal attribution; transitive external dependencies, imported library names, URL/path semantics and lockfiles were not mass-renamed.

Both roots are marked `private: true`; this is metadata-only and does not change application code, ABI, published SDK IDs, package entrypoints, dependencies, workspace relationships, or launch/deployment behaviors.

## Verification — October 25, 2026

- Real graph audit, current main checkout with the proposed change: **PASS**, no unresolved or duplicate workspace dependencies.
- 169 tracked npm manifests; 165 unique named packages; **161 scoped `@flind/` names**, 280 workspace dependency edges; zero inherited `@posthog/` names; zero unresolved edges; zero unprotected Flind scopes.
- **18/18** focused Python regression tests PASS (including 5 new Wave98 root identity tests).
- `git diff --check` and Python test compilation PASS.
- Both original `pnpm-lock.yaml` files preserved unchanged; no dependency installation or lockfile regeneration.

## Resource guard and remaining work

A bounded Mac frontend production build was attempted against the separate Wave84 full frontend checkout, with a Node heap limit. It remained incomplete as temporary build artifacts reduced disk free space below the 10 GiB safety reserve. The build was stopped and only its generated `frontend/dist` output was removed; disk free space recovered to about 14–15 GiB. **Frontend production build is NOT qualified.** It must be repeated on a separate machine or resource-qualified environment, not represented as a success.

This package metadata identity pass is not the zero-legacy-text/full-release gate. Full source and distribution identity, OAuth issuance, first-party domains, real SDK→server ingestion, authorization and browser E2E remain open. Keep private repository and disabled inherited GitHub Actions. No publishing, deployment, paid cloud or removal of legal attribution.
