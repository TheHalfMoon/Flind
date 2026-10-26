# Wave 133 — Explicit AEO tracking domains and first-party package metadata

## Runtime default correction

`posthog/settings/web.py` previously defaulted `AEO_TARGET_DOMAINS` to the donor's `posthog.com` domain. Although the citation-tracking runner separately requires explicit team allowlisting and the `aeo-citation-tracking` flag, an operator enabling teams without overriding domains could unintentionally track the unrelated donor's domain.

**New contract:** default `AEO_TARGET_DOMAINS` is an empty list. Operators may explicitly configure their own comma-separated domain list. No endpoint is invented and no flags, team enrollment or model calls are enabled by this change.

## Metadata correction (not protocol migration)

Four existing **private `@flind/*` workspace packages** use Flind project-maintainer metadata:

- `nodejs/package.json`: Node.js ingestion and processing services, first-party repo/maintainer
- `common/hogvm/typescript/package.json`: Flind logic VM TypeScript integration, first-party repo/maintainer
- `common/hogql_parser/package.json`: first-party query parser description and maintainer
- `common/plugin_transpiler/package.json`: first-party maintainer

No package name, version, dependency, lockfile, script, runtime import or license field is modified. Historical authorship/copyright remains intact in the tracked root `LICENSE` and other source licenses. Legal attribution is exempt from automatic brand erasure.

## Executed verification

On the connected Mac, fetched the exact GitHub branch without modifying the existing sparse checkout. Ran `python3 tools/flind/test_wave133_aeo_metadata.py --ref FETCH_HEAD` using `FLIND_SOURCE_ROOT` to point at the repo. **5/5 PASS**, approximately 26 seconds:

1. Actual `AEO_TARGET_DOMAINS` setting expression evaluates to `[]` with no override.
2. An explicit comma-separated list evaluates to exactly the two supplied domains.
3. An explicit empty override stays disabled.
4. Four target package manifests remain private, Flind-named and JSON-valid with Flind maintainer metadata.
5. Root historical copyright/legal attribution remains in place.

## Outstanding limits

This does **not** independently qualify AEO's scheduler, network traffic, provider billing, production WorkerIngest, Django API or full Flind beta. Keep release blockers #3, #5 and #82 open. No cloud model was invoked, no services deployed, repo private, GitHub Actions inherited workflows disabled, no paid tools.
