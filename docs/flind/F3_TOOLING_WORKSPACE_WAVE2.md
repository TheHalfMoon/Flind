# F3 Wave 2 — Flind test and visual tooling workspaces

## Scope

Rebrand the first-party test harness packages without changing the underlying
Playwright/Storybook third-party dependency implementations:

| Workspace | Package name |
| --- | --- |
| `common/storybook` | `@flind/storybook` |
| `playwright` | `@flind/playwright` |

Both packages now have `private: true`. Their existing dependency on
`@flind/frontend` retains `workspace:*` linkage.

Replaced exact legacy package IDs in the root package commands, development
process configuration, disabled GitHub workflows, e2e specs, Playwright
documentation, Storybook's Vite plugin and source comments. Pnpm lockfile
uses directory-based importer keys for these two packages (`common/storybook`,
`playwright`), so those keys remain unchanged and point at the same
relative frontend workspace dependency.

## Verified locally

- `pnpm --filter @flind/storybook --filter @flind/playwright list --depth -1 --json`
  resolves both renamed packages and reports `private: true`.
- 108 lightweight Python unit/static checks PASS, including four new package
  contract assertions, and eight baseline Flind identity assertions PASS.
- `git diff --check` PASS.

## Still blocked

The workspace has no installed JavaScript dependencies and no complete
runtime stack; real Storybook build, Playwright web journeys, TypeScript
typecheck, dependency lockfile full install, UI screenshots and API integration
were not run. Retained product/third-party dependency namespaces must be
migrated separately with contract, storage and release testing. No release.
