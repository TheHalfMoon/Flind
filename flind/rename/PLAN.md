# Full rename: PostHog to Flind

Owner decision (2026-11-10): everything becomes Flind. File and folder names, the Python package, JS packages, UI
text, configuration, database tables and PostHog's published packages (copied into this repository under Flind
names; nothing is published). It follows the upstream merge of cutoff `4efa693e9aec` (#18).

What stays, as the license requires: the copyright notices in `LICENSE` and `ee/LICENSE`. Provenance stays truthful
(`docs/flind/SOURCE_PROVENANCE.md`): Flind is built from PostHog's open-source code.

## Progress check

`tools/flind/rename_inventory.py` counts what is still named PostHog (paths, occurrences by file type, capitalised
"PostHog"). `baseline.json` holds the counts on `main`; CI fails a branch that raises any of them, and each rename PR
lowers them and rewrites the baseline. Baseline at the start, on `main` 35de3ed: 7,427 paths, 8,948 files with
"PostHog" (44,536 occurrences).

## Stages (one tested PR or PR series each)

1. **Inventory and ratchet** (this PR).
2. **User-facing text.** UI copy, emails, templates, error messages, docs: "PostHog" becomes "Flind". Facts about
   provenance stay truthful.
3. **JS packages and PostHog SDKs.** Vendor posthog-js, posthog-node, `@posthog/icons` and the other `@posthog/*`
   dependencies into the repository as `@flind/*`; nothing is published to npm.
4. **Python package.** `posthog/` becomes `flind/` (merged with the existing `flind/` modules) and every import
   follows; Django settings module, management commands, Celery app names.
5. **Database tables.** Migrations rename every `posthog_*` Postgres table and the ClickHouse tables to `flind_*`,
   with the Django app label; qualified on real services, including a fresh install and an upgrade.
6. **Everything else.** Environment variables (`POSTHOG_*` to `FLIND_*`, with the old names read as fallbacks for one
   release), Docker images and compose service names, Rust crates, Go modules, remaining file and folder names.

## Upstream syncs after the rename

Every later upstream sync applies the same rename map (paths, modules, packages, tables) to the upstream side before
merging, so changes keep landing on the right files.
