# Wave 99 — Desktop scripts must select real renamed Flind packages

## Defect

Following first-party workspace renaming, the root `products/desktop/package.json` still used unqualified `--filter code` / `--filter agent` selectors in dev, package, Vitest and E2E commands. The tracked packages' *actual* names are `@flind/code` and `@flind/agent`; the root monorepo packages are separate private workspaces. The `test:bun` command also selected `@posthog/cli`, which is not a named package in Flind's 169 tracked npm manifests. Unqualified selectors and nonexistent scoped selectors cannot serve as reliable script gates.

## Copy-first correction

- `dev:agent`: exact `@flind/agent`.
- `dev:code`, `package`, `test:vitest`, `test:e2e`, `test:e2e:headed`: exact `@flind/code`.
- `test:bun`: test the existing `@flind/core` only. This explicitly **does not imply any CLI tests passed**; there is no corresponding Flind CLI package in this pnpm workspace.
- Existing `@flind/git`, `@flind/web`, `@flind/electron-trpc`, and dependency build filters are unchanged.
- Do not replace package scripts with new functionality, alter lockfile versions, or touch original donor legal attributions.

## Actual qualification — October 25, 2026

- **23/23** targeted regression tests PASS (new Wave99 tests plus Waves97–98 and graph guards).
- `pnpm --dir packages/agent --filter @flind/agent list -r --depth=-1 --json` returned exactly the private `@flind/agent` package.
- `pnpm --dir products/desktop --filter @flind/code list -r --depth=-1 --json` returned exactly the private `@flind/code` package.
- The targeted package manifests confirm the invoked `dev`, `start`, `package` and `test:e2e` scripts exist; all explicit first-party filter targets resolve in the source package graph.
- The source-level filter errors are fixed. **Full Desktop build, actual Vitest/Playwright browser execution, packages/installers and integrated backend remain unqualified**.

Private repository, disabled inherited GitHub Actions, no publication, deployment, paid cloud or changes to mandatory legal attribution. Issue #82 release gates remain open.
