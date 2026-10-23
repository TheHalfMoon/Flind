# F1 Wave 3 — shared Flind mark and authentication polish

The app-level Logo and Logomark wrappers now render a first-party **text-only Flind mark** rather than importing a third-party artwork component at runtime. The exported props and sizing vocabulary remain available while the UI library is progressively ported. This is an interim mark, **not final approved visual identity**.

The auth welcome logo now navigates within the Flind instance. Invite/signup copy and external footer links were replaced, and the account-mismatch screen identifies Flind.

## Verification
- Shared static test suite: 21 tests PASS.
- Prior identity entrypoint assertions: 8 PASS.
- Four changed TS/TSX sources: TypeScript syntax transpile PASS.
- git diff --check PASS.

## Not validated
- Full TypeScript type-check or React bundle.
- Accessible interactive UI and screenshots.
- Other imported mascot/icon assets outside the shared wrapper.
- All legacy logo paths, vendor library imports or code identifiers.

**Blocker remains:** all active screens, assets and distributed bundles must pass the zero-identity release gate; do not publish.
