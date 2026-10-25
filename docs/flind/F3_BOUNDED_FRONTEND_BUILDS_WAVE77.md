# Wave 77 — Optional bounded frontend build scheduling

## Background

A real Flind frontend build (Wave 76) now gets past the inherited-name
module imports and successfully creates multiple workers, Toolbar,
Render Query and Infrastructure Admin. It still cannot complete the
very large main app bundle on the authorized Mac, because the
free-disk guard correctly stops the process below 11 GiB of free space.

The build already serializes *heavy* app/exporter contexts within
esbuild, but its `buildInParallel` starts every other worker in
parallel. This wave adds a **strict, opt-in production-only** cap to
the number of live build contexts.

## Usage

For a resource-limited developer Mac, with the exact Node 24 and pnpm
11 toolchain and required workspace dependencies already built:

```sh
FLIND_BUILD_MAX_PARALLEL=1 pnpm --filter @flind/frontend run build:esbuild
```

The optional variable accepts only a canonical integer **1–999**.
Malformed or zero values make the build fail rather than silently
disabling the limit. Values above the number of build configs are
capped. **Unset or empty** preserves the original fully parallel
production behavior. In **dev/watch** mode all watchers continue to
start immediately, irrespective of this production-only override.

The small `runBoundedBuilds` worker pool does not duplicate tasks,
drops none, and propagates errors normally. Existing heavy-build
serialization and esbuild callbacks are preserved.

## Evidence, 2026-10-25

- **8/8** synthetic bounded-scheduler tests PASS with real asynchronous
  tasks, default behavior, environment admission, peak concurrency
  1 and 3, no retries of failing tasks, and invalid input rejection.
- Node 24.22.1 and pinned pnpm 11.28.5 were used.
- **Real integration attempted** with
  `FLIND_BUILD_MAX_PARALLEL=1` in an isolated Flind worktree
  containing the built Quill, LogicVM and frontend dependencies.
- The serial build started the very large main application build and
  produced **no esbuild module-resolution error**, but the disk guard
  stopped it after approximately 51 seconds at 10.6 GiB free.
  This was an **incomplete build** and was not a performance win.
  It indicates that the main application's single build graph itself
  can exceed this Mac's conservative available disk headroom. The
  previously tested parallel run also hit its disk floor.
- **Full bundle, full TypeScript check, browser E2E, SDK ingestion,
  full Django schema and release remain NOT QUALIFIED**. Do not
  interpret a partial build as success.

## Operational and legal boundaries

No change to normal default production or development behavior,
no data or backend schema changed, no files sent to external
services, no paid cloud, no deployment or publication. Preserve
required source attribution. Keep repo private and inherited GitHub
Actions disabled. Issues #82 and frontend release qualification remain
open. A machine with more safe disk/CPU headroom, or a separately
qualified modular bundle architecture, is still required for the
full-production-build gate.
