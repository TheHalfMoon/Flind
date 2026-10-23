# F1 Wave 2 — onboarding and invitation identity

**Branch:** `feat/flind-onboarding-email-brand`
**Base:** `b22f3a0cd995f40347586e85cffe0eafcbc21d1f`

## Implemented

- Rename primary onboarding welcome and AI-facing copy to Flind.
- Replace imported mascot artwork on selected welcome, wizard and invitation-preview surfaces with generic graphics or text.
- Rename common sidebar help descriptions, breadcrumb window title and instance status copy.
- Keep the invitation-preview wording synchronized with the actual server-side delegation template.
- Rebrand invitation email headings and links. Replace the old email header image with a Flind text wordmark.
- Remove upstream SaaS help/documentation links from the shared email footer instead of linking Flind recipients to a different company's service.
- Preserve SDK package names, schema identifiers and source path references needed for compatibility.

## Verification performed

- `python3 tools/flind/check_brand_entrypoints.py` — PASS (8 checks)
- `python3 -m unittest discover -s tools/flind -p 'test_*.py' -v` — PASS (7 tests)
- `python3 -m py_compile tools/flind/test_user_facing_brand.py` — PASS
- `git diff --check` — PASS

These are **static tests only**. Django email rendering, frontend compilation, local deployment, integration tests and full end-to-end flows have **not** yet run. A complete runtime build would need an isolated dependency bootstrap, dependency/source verification and more disk resources.

## Remaining F1 and F2 blockers

1. Old logos, favicons, mascot assets, social preview and app-navigation icons remain elsewhere in the imported source.
2. Additional in-product screens, help texts, emails, SDK installation snippets and customer support flows still use the upstream brand.
3. Wizard/AI execution may depend on hosted services or SDKs outside Flind and is unqualified; the copy change does not establish independent operation.
4. Existing internal symbols, API globals, environment variables and schemas remain for compatibility until versioned migrations and adapters are proven.
5. Inherited external links, webhooks, tracking, configuration, billing and SSO services require an audited default-deny outbound dependency review.
6. Full self-hosted first-run and ingestion-to-query smoke tests remain pending.

**Next wave:** categorize all outbound domains and runtime environment defaults; prioritize removing accidental upstream egress before any local launch. Expand first-party Flind branding without silently changing network or data contracts.
