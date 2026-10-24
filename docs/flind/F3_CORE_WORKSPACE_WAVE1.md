# F3 Wave 1 — Flind core pnpm workspace identity

## Scope

Rebrand exactly two **first-party** npm workspace packages together:

| Workspace directory | New first-party npm name |
|---|---|
| `.` | `@flind/root` |
| `frontend/` | `@flind/frontend` |

Both manifests are `private: true` and carry Flind repository, issues,
homepage, author and descriptions. Legal LICENSE files remain intact.

## Integrated migration

Updated every exact reference to the former root/frontend workspace package
name in tracked source, including:

- pnpm lockfile's Storybook and Playwright importer dependency keys, preserving
  their existing `workspace:*` versions and relative links
- root package build/test scripts, Storybook/Playwright scripts and manifests
- `hogli.yaml`, shell wrappers, Docker build filters, internal typegen and
  frontend build tooling
- inherited disabled GitHub workflows and depot workflows, so future re-enable
  must not accidentally address an undefined package
- tests, development documentation, agent skills and downstream tools

Other `@posthog/*` dependencies, embedded protocol identifiers, Python
modules, data storage names and third-party SDK packages are **not** renamed
here: migrating them without a complete dependency/runtime/database graph
could break builds or data integrity. Separate first-party migration waves
must explicitly qualify those contracts.

## Local evidence

- `pnpm --filter @flind/frontend list --depth -1 --json` resolves the
  expected frontend workspace and reports `private: true`.
- `pnpm --filter @flind/root list --depth -1 --json` resolves the root
  workspace and reports `private: true`.
- 104 dependency-free Python tests PASS including five workspace/lockfile
  assertions.
- 8 brand foundation checks PASS.
- Changed Python source modules compile.
- `git diff --check` PASS.

## Limitations

No dependency install or full pnpm build, TypeScript typecheck, Storybook,
Playwright browser/E2E or backend integration tests were run. Existing
third-party library namespaces remain until migrated with their own
functional test gates. Source-wide identity gate is still FAIL and release
is **NO-GO**. No publication.
