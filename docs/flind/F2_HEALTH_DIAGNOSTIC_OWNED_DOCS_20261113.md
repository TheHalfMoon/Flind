# Health diagnostics: owned documentation-only URLs

Scope: Flind frontend health diagnostics and session-recording disabled
explanations. This is an isolated first-party navigation hardening change,
not a feature removal or release.

## Surfaces

- Web analytics health check table: five external help links now derive from
  `flindDocsUrl` or `flindDocsSectionUrl`. Internal Settings and
  Review Suggestions links still use local Flind app routes.
- Health category details: six documentation destinations are derived from
  the same exact-host, HTTPS-only helper. Existing local drill-down links and
  category content remain intact.
- Session replay disabled guidance: optional first-party section URLs,
  including recording troubleshooting; when no first-party documentation
  has been configured, the interface renders actionable plain-language
  guidance rather than navigating users to inherited upstream docs.

Only an explicitly configured first-party HTTPS documentation URL and
matching exact configured host can generate a link. These helpers already
reject userinfo, wrong schemes, unexpected ports, lookalike domains and
invalid paths. This patch does **not** assert that every deep-link page
actually exists: the operator must provision and verify Flind docs
before enabling those settings.

## Checks

`node --test frontend/bin/flind-health-doc-isolation.test.mjs`
checks four source contracts and fails if these three surfaces regain
literal inherited provider documentation. The dedicated GitHub Actions
workflow checks this source contract. The existing frontend workflow
runs full Jest and relative TypeScript regression checks on this branch,
including the URL helper and recording-button unit tests.

The source contract does **not** substitute for a built browser E2E,
full network-egress trace or deployment qualification. Remaining
third-party links elsewhere in the source tree are not addressed.
Preserve the upstream copyright and license information.

NO PUBLIC RELEASE, PACKAGE, TAG OR PRODUCTION DEPLOYMENT without
the owner's explicit `GREEN LIGHT FLIND`.
