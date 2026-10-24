# Flind F3 Wave 14 — local WASM query parser dependency

## Dependency mismatch found by the supply-chain gate

The frontend originally depended on a released, compiled WebAssembly parser
package at version **1.3.88**, rather than the unbuilt parser source under
`common/hogql_parser`. Simply renaming the package to
`@flind/query-parser` made pnpm look for a nonexistent new package in the
public npm registry. The no-downgrade trust gate correctly refused it.

## Source-first remedy

- Verify the existing upstream MIT-licensed version 1.3.88 package tarball
  against its published **SHA-512 SRI**:
  `sha512-zygPFNMJVxeiOdO1zW2mPK4A2fBS2qCaNvGK9B7Fan1mrW5C6cK2ESc22qf/+aiGS+8IMe6xvkmGwCjzoU2GQw==`.
- Vendor only the five **compiled WASM glue/runtime and type declaration**
  files into `common/hogql_parser/dist/`. No upstream npm registry access
  is needed once the files are checked out and built into the frontend.
- Add `common/hogql_parser` to the root pnpm workspace, and point
  `frontend/package.json` to `@flind/query-parser: workspace:*`.
- Replace the published dependency's lockfile snapshot with an actual
  local `link:../common/hogql_parser` workspace edge.
- Update parser metadata's homepage, issue tracker and repository pointers
  to the Flind repository. Original factual MIT/copyright author
  attribution stays intact; do not misrepresent third-party provenance.

## Actual validation on macOS

- Node 24 compiled parser smoke test: initialized the CommonJS factory and
  `parseSelect("SELECT 1")` returned a `SelectQuery` AST.
- All three shipped glue runtimes were checked not to contain unsafe
  `new Function(` or Emscripten's dynamic-evaluation error sentinel.
- pnpm `--lockfile-only --offline --frozen-lockfile --ignore-scripts`
  **PASS**, original trust policy retained, **3,981 entries** verified.
  The root pnpm install now recognizes **131 workspace projects**.
- Per-file SHA-256 integrity is verified in
  `tools/flind/test_local_query_parser_wasm.py`.

## Remaining limitations

This is an imported, verified compiled artifact, **not** a new independent
WASM compiler build from Flind source. A fully reproducible first-party
Emscripten build, binary provenance verification, real frontend typecheck,
Jest, browser CSP journey, release packaging and end-to-end API semantics
are still needed. Keeping original legal attribution is required.

No external Flind npm publication was invented or attempted, and no paid
cloud used. Private repository, inherited Actions disabled. **NO-GO**.
