# Wave 164 — Offline, bounded sparse Django source diagnostics

## Problem

Flind's Django registry qualifier imports tracked Python source from a partial Git checkout. The original code called `git show` and `git ls-tree` without disabling Git's *promisor lazy blob fetching*. A supposedly local, socket-denied Django probe could therefore unexpectedly trigger Git-network object fetches, run into slow blob downloads, and obscure the specific first-party file that was unavailable. The previous probe recorded only a generic `ImportError` with 12 traced modules.

## Fix

- All `git ls-tree` and `git show` operations now use `GIT_NO_LAZY_FETCH=1` and `GIT_TERMINAL_PROMPT=0`, so missing partial-clone objects are not silently downloaded during the read-only probe.
- Missing local Git blobs, oversized/non-UTF-8 source and Git read timeout now record a short, sanitized `source_failure_kind` and an exact **repo-relative** `blocked_tracked_source` when known.
- Unqualified attempts can record `last_traced_source` as diagnostic context, explicitly **not** proof it was the failed module; safe `ImportError.name` fields and source import deadline/limit codes are surfaced without host file paths, credentials or exception text.
- The parent process passes these safe fields to the final JSON report without changing the release decision. A successful registry alone will never qualify migrations, API/E2E, tenant separation or release.

## Execution and evidence — 2026-10-27, Mac

The exact proposed source was copied directly from the private GitHub PR branch into `/private/tmp/flind-wave164-runner/tools/flind`. Existing Python 3.14.7 / Django 5.2.18 pinned environment was used; no new dependencies or large Git trees downloaded.

**Original tool unit suite: 9/9 PASS, exit 0.** Three new tests verify all Git reads prohibit lazy fetching, missing Git blob errors report safe relative paths, and timeout paths are identified. The original Git fixture import also checks `last_traced_source`.

A real, read-only, socket-denied Django registry attempt against the **older detached sparse Wave140 checkout** with max 75 imported modules and 45-second child timeout reported:
```json
{
  "phase": "sparse-git-django-app-registry",
  "blocker": "ImportError",
  "traced_source_modules": 10,
  "django_registry_qualified": false,
  "migrations_qualified": false,
  "app_http_qualified": false,
  "release_qualified": false
}
```
It did **not** identify a specific missing Git blob, so this result must not be attributed to a particular file. A further 20-second bounded check using the final diagnostics revision returned `blocker=Bounded Django registry probe timed out`, again with no completed registry. The final revised code was fully unit tested, but the final 20-second runtime attempt is insufficient to prove an import fix.

Disk free space was observed falling to approximately 2.9 GiB during the attempted registry boot, later recovering to approximately 3.9 GiB; no whole-tree expansion or installation was attempted. To protect the shared low-resource Mac, no more heavy registry restarts were attempted.

## Outstanding work

**Issue #82 remains release NO-GO.** The next material step requires safely available complete first-party Python source on a sufficiently provisioned authorized machine or a bounded object-prefetch strategy, then actual `django.setup()`, migration/rollback with disposable database, and SDK→Kafka→ClickHouse→authenticated API→Dashboard tenant-isolated E2E. None was accomplished by this tool fix. Identity issue #5, first-party real OAuth/PKCE, UI qualification and package tests also remain open. Repo stays private; GitHub Actions unchanged/disabled; no publishing, deployment or paid services; legally required attributions preserved.
