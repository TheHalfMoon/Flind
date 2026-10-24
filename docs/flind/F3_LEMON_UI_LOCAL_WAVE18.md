# F3 Wave 18 — first-party Flind UI workspace

## What changed

The final inherited-scoped internal npm manifest was a UI component library.
Its consumers previously resolved a **published compiled** package rather
than the repository's unbuilt source. A name-only replacement would break
installs. Instead, the source workspace moved to
`frontend/flind/lemon-ui`, with the private name `@flind/lemon-ui`.
Nineteen product consumers now explicitly use `workspace:*`. TypeScript,
Jest, Storybook and type-definition update paths follow the new location.

The local package contains five verified, compiled compatibility artifacts:
JS, TypeScript declarations, CSS and two font files. They were obtained
from the MIT-licensed public package version 0.0.0 with published SRI
`sha512-SJaquP2UGsfOx33d7SssxNvUTfDT5VWWBEzWyHvJXaFrHNZd3ZeRrHLzsETXjhJO3ZcsVdoJD+tm27B6Qe5GuQ==`.
Per-file SHA-256 checks live in `tools/flind/test_local_ui_wave18.py`.
Keep factual author/copyright notice and original MIT license intact.

The root pnpm workspace now contains the UI package. The root lockfile
links every consumer locally and no longer includes the published UI
snapshot. The obsolete nested lockfile was removed. Its build helper
import path was corrected for the new source location.

## Execution and boundaries

- Five local source/integrity/graph/JS syntax checks were executed.
- Frozen offline pnpm lockfile-only check **PASS** with the original
  no-downgrade trust policy and **3,980** audited entries.
- All 159 tracked first-party npm package names now use Flind identity,
  and the graph has no unresolved `workspace:*` references.
- This is a **published compatibility artifact**, not yet a reproducible
  Flind source build. A proper esbuild/tsup build from repository source
  and browser stylesheet/component tests are separate qualifications.
- The bundle has peer dependencies on React, ReactDOM and Ant Design
  and runtime references to Kea / Kea Router; package manifests retain
  those contracts. No package was published.

## Release remains NO-GO

The package-name gate passing does NOT mean the entire source, assets or
built artifacts are independently branded. API/SDK compatibility, frontend
typecheck and Jest, Django migrations, browser Playwright, live egress
tracing, Electron builds and signed OS installers still require validation.
Keep repository private and inherited GitHub Actions disabled; do not
deploy or publicly release.

## Additional install qualification

The first frozen lockfile-only check did not detect a missing tsup dependency
snapshot. An actual filtered package install caught it. The lockfile was
repaired using pnpm --fix-lockfile without disabling no-downgrade trust
policy, then the public npm registry provided the missing files. A filtered
installation of @flind/lemon-ui and the bundled assets completed, with
React/Ant Design/Kea package prerequisites present. A direct Node require
of browser-targeted UI failed with window is not defined, as expected for
a DOM-dependent package. A real browser/jsdom component render is **NOT**
claimed or qualified by this result.

## Requalification on 2026-10-24 (macbook)

- Full Python regression: **221/221 passed**, rerun after updating Wave 17 expectations.
- `pnpm install --frozen-lockfile --offline --lockfile-only --ignore-scripts`: **passed**; supply-chain policy enforced.
- `git diff --check` and `git diff --cached --check`: **passed**.
- Migration diff audit: **3,686 TS/JS hunks**, only the two expected path-alias changes in Storybook and Jest differ from direct import-name substitution.
- All five compiled compatibility artifacts are present and staged with byte-level regression hashes.
- `pnpm --filter @flind/lemon-ui typecheck`: **not qualified**. Node 26 aborted at the default approximately 2 GiB V8 heap. Retried with the project's Node 24.15.0 and a 4 GiB heap; it also aborted due to V8 JavaScript heap exhaustion on the 8 GiB Mac. No TypeScript PASS is claimed. Isolate type checking or use a suitable higher-memory environment before release.
- Runtime/browser and reproducible source compilation are **not qualified** by this wave.
- GitHub repository visibility was independently verified private; GitHub Actions are disabled. No deployment or public release.
