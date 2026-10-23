# Flind — zero legacy identity release gate

## Product rule

Flind must ship under its own brand in source-owned product surfaces, SDKs, examples, docs, API metadata, event destinations, desktop/mobile apps, deployment assets and installers. The target is **zero** legacy vendor references in the active source tree and packaged outputs.

This gate is **currently FAILING**. A complete copied source is the beginning of the port, not a completed rename.

## Reproducible inventory

```bash
python3 tools/flind/brand_audit.py
python3 tools/flind/brand_audit.py --strict
```

At the `734593b42f17` baseline the tracked-file inventory found **31,192** text files with the old identity and **7,089** tracked paths whose names contain it (categories overlap). The scan does not cover untracked files, binary contents, Git history, generated deployment images or SDKs in separate repositories.

The checker does not silently ignore modules, lockfiles, agent instructions or third-party notice files. Legal notices require rights review and must not be falsified or silently erased.

## Ordered migration and acceptance

| Grain | Change | Minimum release test |
| --- | --- | --- |
| Z0 | Remove upstream cloud defaults and user-visible app metadata | Local/default configurations cannot point to another vendor |
| Z1 | Flind login/onboarding/emails/docs/icons and owned public assets | Browser and email screenshot crawl reports zero old visible brands |
| Z2 | Rename first-party client modules, hosted settings and service URLs | Mobile/desktop/CLI cannot send data without an explicitly configured Flind destination |
| Z3 | Migrate names in first-party Python modules and Django app labels | All Django imports, migration graph and upgrade-from-baseline restore tests pass |
| Z4 | Rename JS/Node/Rust/Go packages, APIs, import paths, generated clients and SDKs | Package installs, lockfile, builds, contract tests and existing data migrations pass |
| Z5 | Rename dashboards, analytics events, outbound integrations and internal deployment wiring | Ingest-to-query tests, egress-deny tests and full-stack replay/flag tests pass |
| Z6 | Eliminate old marks from all binaries and shipped pages; audit all tracked files | Zero source/path scanner findings, zero production artifact strings, clear notices review |

**No blanket substitution**: editing a package name without its import graph, a persisted database table without its migration, or a protocol key without its clients is a regression. Whole-module moves happen as atomic tested dependency slices.

## Release status

- Initial product-brand and invitation surfaces: partial
- Central cloud default containment: partial and static-test-backed
- Full local boot: NOT verified
- Source-wide zero legacy references: FAIL
- Retained original files in historical commits: NOT reviewed for rewrite
- Rights and attribution of included dependencies: must be reconciled before publication
- Production release: NOT authorized
