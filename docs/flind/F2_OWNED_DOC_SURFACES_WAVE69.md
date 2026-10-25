# Wave 69 — First-party help destinations in high-traffic product flows

## Product changes

This scoped wave removes direct inherited-vendor documentation URLs from
three active Flind frontend surfaces:

1. Product Tours → language/localization panel (both empty and populated
   translation states). It now conditionally displays a docs link only
   when `flindPublicUrl('docs')` resolves an operator-configured Flind
   HTTPS origin.
2. Web Analytics → conversion warning for events missing `$session_id`.
   It gives standalone actionable guidance even when Flind has no public
   docs URL configured. Optional help is first-party only.
3. Web Analytics → live-user-count indicator. Its help destination is
   now `flindPublicUrl('docs') ?? undefined`, preserving the component's
   documented optional `docLink` prop and disabling the link without
   a verified first-party docs site.

The existing `flindPublicUrl` helper validates strict HTTPS, hostname,
port, userinfo and fragments. No invented documentation routes or owned
domains are introduced. The visible labels and product behavior remain
usable without a configured docs host.

## Verified local evidence — October 25, 2026

- 5/5 new scoped source-contract tests PASS.
- 3/3 edited TSX files parse successfully with the TypeScript/JSX Babel
  parser in a disposable JavaScript parser environment.
- `git diff --check`: PASS.
- Direct inherited `posthog.com/docs` destinations absent in all three
  edited components.
- Full TypeScript typecheck, production Vite build, real click-through
  and browser network egress **not qualified** because the full frontend
  dependency tree is not installed in the isolated checkout.

## Remaining blockers

Issue #24 remains OPEN for the many other active help/doc links and
independent no-upstream-egress browser proof. This wave does not imply
full source identity cleanliness (issue #5) or any release readiness.

Keep TheHalfMoon/Flind private, inherited GitHub Actions disabled;
no public publication, deployment, paid services or legal attribution
stripping. Do not substitute donor site URLs as a fallback.
