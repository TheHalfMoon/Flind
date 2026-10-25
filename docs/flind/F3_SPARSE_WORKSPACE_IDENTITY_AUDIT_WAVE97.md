# Wave 97 — Audit the complete npm workspace graph in sparse private checkouts

## Problem

A lightweight `git clone --filter=blob:none --sparse` of Flind is preferable on the shared 8 GiB Mac with limited free disk. The existing `check_workspace_links.py` rejected any tracked `package.json` absent on disk, even when Git marked it as intentionally unmaterialized (`skip-worktree`). This prevented a definitive current-main workspace-identity check without expanding the entire repository.

## Implementation

- Enumerate every tracked manifest with Git `ls-files -t -z` to distinguish intentionally sparse `S` entries from normally checked out `H` entries.
- When present locally, inspect the working-tree manifest, preserving existing semantics for local uncommitted changes.
- For an absent **S** entry only, read the exact indexed blob via `git show :path`; this never materializes the file, changes checkout state, or pulls content from an unrelated branch.
- Keep **H** entries with missing files a hard failure (e.g. an accidental or intentional working-tree deletion). Invalid or inaccessible blob JSON still fails closed.
- No node_modules install, package renames, lockfile changes, registry access or release claims.

## Current main qualification — October 25, 2026

Against latest private main commit `3e2e7f2c`, using the small sparse checkout, the real `--require-no-legacy` graph audit returned **exit 0** twice:

| Metric | Observed |
|---|---:|
| Tracked npm manifests | 169 |
| Unique named packages | 165 |
| Named `@flind/` packages | **159** |
| Workspace dependency edges | 280 |
| Remaining inherited `@posthog/` package names | **0** |
| Broken workspace edges | **0** |
| First-party Flind packages not marked private | **0** |
| Package graph / package identity gates | **PASS / PASS** |

Focused 13/13 tests PASS, including six new tests for sparse manifests, deleted worktree files, index corruption, malformed status, precedence of local files, and graph integrity. The full legacy workspace source test suite requires a complete checkout because it opens additional runtime files; its FileNotFoundErrors in a sparse checkout are not equivalent to code failures.

## Scope

This is the npm package name and workspace graph gate **only**. It does not establish zero inherited identity in filenames, API routes, runtime strings, SDK wire formats, binaries, Git history or mandatory legal notices. It also does not qualify frozen-install production builds, browser E2E or SDK→backend ingest. Leave the full-source identity and release issues open until their separate gates pass.

Private repository, inherited GitHub Actions disabled, no paid providers, deployments or publication. Required legal source attribution remains untouched.
