# Upstream security fixes to integrate first

Range: Flind import `cd26680c` to the pinned cutoff `4efa693e9aec` (4189 commits). Found by scanning every commit
subject in the range for security terms (114 matches) and keeping only commits that fix or harden security
behaviour; feature commits that merely mention exposure, tokens or permissions are excluded.

Each is integrated in its own PR: cherry-pick (or re-implement where Flind changed the same files), keep the
upstream test, add one if upstream had none, and run the relevant suites. `status` is updated per PR; batch 1 merged as #11, batch 2 merged as #12, batch 3 is the `flind-ci/upstream-security-batch3-20261110` PR.

| Upstream commit | Area | Class | Fix | Status |
| --- | --- | --- | --- | --- |
| [`98bfb2f0c`](https://github.com/PostHog/posthog/commit/98bfb2f0c) | replay | secrets | Redact destination secrets from recorded network bodies | merged (#12), cherry-picked |
| [`ace059329`](https://github.com/PostHog/posthog/commit/ace059329) | groups | access control | Apply property access control to group properties | pending |
| [`c1acb07d4`](https://github.com/PostHog/posthog/commit/c1acb07d4) | activity-log | access control | Apply property access control to logged group property values | pending |
| [`5666872eb`](https://github.com/PostHog/posthog/commit/5666872eb) | persons | access control | Apply property access control to properties_at_time | cherry-picked (batch 3) |
| [`736a4e51a`](https://github.com/PostHog/posthog/commit/736a4e51a) | hogql | access control | Mask restricted person properties inside `$set` and `$set_once` (found as a dependency of `5666872eb`) | cherry-picked (batch 3) |
| [`b17ccdae5`](https://github.com/PostHog/posthog/commit/b17ccdae5) | flags | access control | Apply property access control to test-evaluation person properties | merged (#11) |
| [`4d7475936`](https://github.com/PostHog/posthog/commit/4d7475936) | data-warehouse | information disclosure | Sanitize repartition permission denials | merged (#11) |
| [`b169def24`](https://github.com/PostHog/posthog/commit/b169def24) | permissions | access control (UI) | Disable admin-only setup controls for non-admins | merged (#12), adapted |
| [`7461fb838`](https://github.com/PostHog/posthog/commit/7461fb838) | api | secrets | Show the secret API token only to callers with its scopes | cherry-picked (batch 3) |
| [`949424276`](https://github.com/PostHog/posthog/commit/949424276) | cdp | secrets | Mask secret fields in object-shaped plugin config schemas | cherry-picked (batch 3) |
| [`20661a999`](https://github.com/PostHog/posthog/commit/20661a999) | cdp | secrets | Leave secret inputs out when duplicating a function | pending |
| [`ae03c789d`](https://github.com/PostHog/posthog/commit/ae03c789d) | mcp | secrets | Redact secrets from CI failure-log and broken-tests responses | cherry-picked (batch 3) |
| [`514b2c621`](https://github.com/PostHog/posthog/commit/514b2c621) | tasks | secrets | Redact clone diagnostics | cherry-picked (batch 3) |
| [`e4894f80e`](https://github.com/PostHog/posthog/commit/e4894f80e) | security | SSRF | Refuse hosts on the out-of-band domain list | pending |
| [`9bfbac633`](https://github.com/PostHog/posthog/commit/9bfbac633) | security | SSRF | Bound the host length in the node out-of-band matcher | merged (#11) |
| [`b75010ee2`](https://github.com/PostHog/posthog/commit/b75010ee2) | security | SSRF / host header | Keep absolute_uri and CSV export requests on site_url | cherry-picked (batch 3) |
| [`e2ad511e2`](https://github.com/PostHog/posthog/commit/e2ad511e2) | saml | authentication | Use an opaque token for SAML relay state | merged (#11) |
| [`a3f2a2e71`](https://github.com/PostHog/posthog/commit/a3f2a2e71) | flags | tokens | Clear the old token's team metadata cache on token reset | pending |
| [`99878c1a8`](https://github.com/PostHog/posthog/commit/99878c1a8) | review-hog | tokens | Scope GitHub tokens to read or push per step | pending |
| [`44829da3e`](https://github.com/PostHog/posthog/commit/44829da3e) | mcp | consent | Read AI consent from the project for scoped tokens | cherry-picked (batch 3) |
| [`69f66d427`](https://github.com/PostHog/posthog/commit/69f66d427) | ingestion | tenant isolation | Keep team id and token lookups apart in TeamManager | merged (#12), adapted |
| [`fee9132a5`](https://github.com/PostHog/posthog/commit/fee9132a5) | security | abuse | Match block rules against look-alike dots in email domains | merged (#11) |
| [`c69dd9abe`](https://github.com/PostHog/posthog/commit/c69dd9abe) | error-tracking | prompt injection | Harden issue summaries against prompt injection | merged (#12), re-implemented |
| [`11742b8e0`](https://github.com/PostHog/posthog/commit/11742b8e0) | livestream | CVE | Disable multipath TCP on listeners (CVE-2026-98432) | merged (#11) |

24 fixes (23 from the subject scan, plus `736a4e51a`, found as a dependency). Commit subjects only were scanned; fixes whose subject does not name the issue can be missed,
so the area integrations in later steps still review every security-relevant module they touch.
