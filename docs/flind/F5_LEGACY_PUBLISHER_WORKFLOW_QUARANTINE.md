# Inherited publishing workflows quarantined before Flind release

Status: **15 previously active upstream release/publish workflows have
been moved verbatim out of GitHub's runnable workflow directory**.
No Flind publication, deployment, tag or install artifact is authorized.

## Why this matters

A codebase rename does not convert the old registry destinations,
package ownership, installer channels or release credentials. Flind
inherits GitHub Actions definitions which can distribute artifacts
under original upstream names or to registries that are not Flind-owned.
Some accept `workflow_dispatch`, and others respond to specific
legacy tags or branches. Relying exclusively on a current upstream
repository-name guard is unsafe if it is subsequently edited during
the wider Flind rename.

## This checkpoint

The 15 explicit legacy release/publish workflows in
`tools/flind/quarantined_release_workflows.json` have been moved
**without altering their content** from `.github/workflows/*.yml`
to `.github/quarantined-release-workflows/*.yml.disabled`.
GitHub Actions no longer recognizes them as runnable workflows.
The inventory pins the exact original Git blob SHA-1 for each file,
and a no-secrets source-only CI check ensures none is silently restored,
removed from the archive or referenced by a runnable workflow.
The check also runs when workflow files change on `main` or a PR.
Normal Flind validation, migrations, frontend tests and SDK smoke
workflows remain in the active folder.

The quarantined set includes explicit releases for the Rust CLI,
desktop apps, Python packages, npm packages, a Rust crate, parser
build/publish flows, installer assets, and other inherited publishers. The set also includes the **unguarded
weekly Playwright image mirror**, which attempted to push directly to an
upstream-owned GHCR namespace on its schedule or manual dispatch.
Reactivation must be an independent PR with actual Flind package
names, first-party destinations, ownership, provenance, reliable
builds, security/egress reviews and owner approval.

## Important incomplete audit

This is **not** a comprehensive 200-workflow publication audit.
Mixed build/CD workflows such as
`ci-agent-skills.yml`, `cd-metrics-agent-image.yml`, and other
deployment or external registry definitions remain enabled and require
a separate job-level review before any public deployment.
Do not interpret this quarantine as proving the repository has
zero possible outbound writes, secret exposure or deployment paths.

The public CLI is also still marked release NO-GO, and its compiled
bundle and source-map uploads are not qualified for distribution.
Do not tag, create GitHub Releases, run deployments, publish npm/PyPI/
crates packages, upload signed installers or submit app-store packages
until the user explicitly authorizes `GREEN LIGHT FLIND`.
Retain legally required copyright, NOTICE, provenance and licenses.
