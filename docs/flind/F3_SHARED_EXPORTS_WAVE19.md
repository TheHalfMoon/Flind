# Flind Wave 19 — shared exports stay within Flind

## Scope
- Correct the dashboard, insight, and notebook shared/exported HTML titles to `Flind` while retaining the existing whitelabel override.
- Eliminate inherited marketing hyperlinks in the dashboard/embed/notebook header logo and shared-dashboard credit. Keep the native Flind logo and local credit without inventing an unowned destination.
- Preserve the established `posthog:dimensions` cross-frame event identifier as an explicit compatibility boundary; migrating a wire contract requires consumer tests first.

## Qualification
- `tools/flind/test_exporter_brand_wave19.py` verifies all three titles, absence of inherited marketing links, native logo/credit, and preservation of embed event compatibility.
- Scoped static tests do not replace real browser rendering, screenshot diffs, URL egress tracing or external embed consumer tests.
- The source-wide external destination gate continues to fail until remaining independent files are migrated.

## Release
Not release-qualified. No deployment or package/public release. Private repository and disabled inherited Actions unchanged.
