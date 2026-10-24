# Wave 20 — contain inherited hosted-cloud upsell

The self-hosted account menu previously invited users to a different vendor's hosted service. The bookmarked `/move-to-cloud` route also loaded a vendor-specific upsell and contained a signup destination and compliance assertions unrelated to Flind.

## Scope
- Remove that dropdown upsell (and now-unused imports/state).
- Keep the existing URL route for bookmarks and internal contracts, but display a truthful Flind message that hosted migration is unavailable.
- Remove inherited service links, marketing copy and unsupported vendor compliance claims from that route.
- Preserve scene/route enum IDs until dependent consumers can be migrated with tests.

## Verification and deferred risks
- Regression tests prevent the upstream signup from returning to the active account menu or route.
- Full Python, TSX syntax checks, and `git diff --check` are required before merge.
- Real browser navigation, analytics network traces and a comprehensive cloud integration audit remain separate release gates.
- Repository remains private. Actions stay disabled. No deployment/public release.
