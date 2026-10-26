# Flind — first-party identity contract

**Status:** Active project rule for development, review, testing and release preparation. This document is the durable implementation of the founder's instruction: **everything first-party must carry the Flind identity**.

## Required Flind ownership

Every new or migrated first-party surface must identify the product as **Flind**, including:

- User-facing UI, onboarding, Desktop, mobile, emails, installers, screenshots and documentation
- First-party Python distribution and JavaScript/native package metadata, product logs, CLIs and command names
- First-party Git repositories, ownership metadata, support/community entrypoints, icons, naming conventions and product assets
- Product-owned authentication origins, OAuth issuers, API and SDK endpoints, redirects, install/update channels and deployment domains
- Worker/service names, release artifacts, Docker/container images, telemetry, export archives and generated bundles

No upstream/donor product branding, homepage, credentials, analytics, telemetry, release destination or cloud host should be **introduced** as a new first-party default. Do not invent a Flind domain or turn on external services without owner-controlled configuration and verified tests.

## Migration safety rule

Legacy source code can still contain protocol-bound or schema-bound identifiers. Never blanket-rename:

1. Python import paths, Django app labels, migration dependencies, model table names, persisted user/project data and feature-flag keys
2. Public SDK package names and binary/client wire contracts
3. OAuth/PKCE issuer, callbacks, token audience and API routes
4. Active DNS/HTTP endpoints, project-owned credentials, community/install/update services and publishing targets

Instead, implement a compatible, tested Flind-owned replacement, migrate persistent references and dependent services, verify rollback, and then remove the historical runtime identifier. These exceptions are **temporary technical debt, not brand approval**. Track and complete them in GitHub issue #5. Backend/product release proof is separately tracked in GitHub issue #82.

## Legal attribution exception

Preserve legally required copyright, original LICENSE/NOTICE and third-party attribution. Those legal records are not first-party marketing content and must not be rewritten to falsely claim authorship or strip obligations.

## Validation gates

- `tools/flind/test_flind_identity_contract_wave143.py` — checks first-party root distribution identity and 18 already-migrated private workspace manifests. It is a *regression subset*, not a project-wide pass.
- `tools/flind/brand_audit.py --strict` — project-wide tracked source identity gate; **expected FAIL until remaining migrations are completed**. The tool does not scan Git history or every binary artifact.
- Qualify any runtime-bound migration through original build/contract/integration and E2E tests. Never claim release-readiness merely from metadata checks.
- Publication/deployment remain prohibited until explicitly requested. Keep GitHub repository private, inherited Actions disabled, preserve notices and use no paid services without explicit permission.

**Only Flind is the intended final product identity.** Do not treat an upstream identifier as a permanent alternative product name.
