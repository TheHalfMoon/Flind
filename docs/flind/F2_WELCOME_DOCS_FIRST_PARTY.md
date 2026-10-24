# Flind F2 — welcome documentation routes (no external provider)

Three first-run surfaces previously used inherited, live external docs links:
the flagship-product cards, the products-in-use pills, and the provisioned
welcome notice. All product branding entries and the fallback linked into
the upstream documentation service.

## Change

- Central product metadata now uses the operator-approved
  `flindPublicUrl('docs')` destination. The existing first-party HTTPS host
  allowlist applies. There are no guessed product subpaths or unowned docs.
- If no Flind documentation URL is configured, the flagship cards,
  active-product pills and provisioned welcome strip render **static,
  non-interactive** entries. They do not open a blank tab or third-party URL.
- If the operator does configure a Flind docs URL, product entries remain
  normal links; their existing click instrumentation is preserved.
- First-run marketing headings say Flind, not the source product.

## Test and release boundary

`tools/flind/test_welcome_docs_identity.py` guards all three navigation
surfaces and the ten product/fallback documentation definitions.

The available GitHub-only execution context cannot run full frontend
typecheck, Jest, Storybook or browser E2E because the previously authorized
desktop execution quota is exhausted. Source and diff checks do not replace
a successful production build. Any actual Flind documentation website
must exist at an operator-controlled and verified URL before it is enabled.

Other onboarding, integrations and product manifests still contain inherited
documentation references. The full identity and release gates remain
**NO-GO**. Keep the repository private; do not publish.
