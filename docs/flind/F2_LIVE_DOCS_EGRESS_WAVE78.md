# Wave 78 — First-party documentation and help surfaces

## Scope

The Support, Customer Analytics, and Signals/Scouts interfaces still
contained hard-coded outgoing links to the donor's public docs,
community forum and scout helper GitHub repository. This wave moves
**12 product documentation surfaces** plus the Tickets scene to the
already existing Flind-owned host contract.

These are live application code paths, not release/build notes or
mandatory legal attribution. No donor license or required NOTICE file
was touched.

## URL ownership contract

`flindDocsUrl(relativePath)` composes an explicitly configured
`flindPublicUrl('docs')` with a static, validated relative page slug.
The base requires both `VITE_FLIND_WEBSITE_HOST` and
`VITE_FLIND_DOCS_URL` to be operator configured with the exact same
first-party host, HTTPS, and no custom port/userinfo/fragment.
Deep links reject absolute URLs, leading slashes, empty path segments,
traversal, encoded URL shortcuts, query and fragment injection; no
unconfigured or inherited fallback host is used.

Unconfigured docs mean:
- Product empty-state links, help actions, report examples, scouts/MCP
  installation guidance and identity badge doc links are omitted.
- Admin/product setup local actions continue to work where present.
- Tickets shows a Flind community URL only when it is configured and
  accepted by the same first-party URL validator; otherwise the scene
  directs users to their instance administrator.
- Scout helper footer always offers internal **Manage scouts**. Donor
  skill repository links are not shown as Flind skills, because no
  approved Flind-hosted equivalent has yet been configured.

Backend identity `AgentRosterGroup.id='posthog'` is intentionally
**preserved** as an internal compatibility key; the visible group label
is now **Flind data**. Do not rename schema keys without backend/
API migration evidence. Visible product copy no longer claims
PostHog's identity verification or AI ownership.

## Verified on October 25, 2026

- 38/38 actual Jest unit checks for Flind public links, including
  deliberately malicious relative docs paths and absent configuration.
- 14/14 existing ProductEmptyState behavior tests PASS.
- 2/2 direct Jest runtime checks for the agent roster's visible Flind
  identity, stable internal group keys and absent fallback docs URLs.
- 40/40 existing FeaturePreviewSceneGate behavior checks PASS.
- **94/94 actual targeted Jest checks PASS** over four suites in total.
- 5/5 Node 24 source/TypeScript AST contract checks PASS across all
  twelve migrated docs surfaces plus the Tickets scene.
- File-level formatting (oxfmt), whitespace and source scans required
  to complete before GitHub merge.
- Full browser egress under real deployment, full frontend typecheck,
  full production bundle and exhaustive link inventory are **NOT
  qualified**. Issue #24 therefore remains OPEN.

## Operating constraints

No public release, cloud provisioning, paid services, new document
domain, or change to user data. GitHub repository stays private,
inherited GitHub Actions disabled. Mandatory original source notices
remain intact. Broader release remains **NO-GO** until all backend,
browser, security and E2E gates pass.
