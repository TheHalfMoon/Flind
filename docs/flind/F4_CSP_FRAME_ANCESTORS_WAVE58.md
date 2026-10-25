# Wave 58 — Do not allow inherited external origins to frame Flind

## Problem

Flind's Django Content-Security-Policy still allowed the original
vendor's main and preview origins as trusted frame ancestors for
application pages. A separate legacy developer-domain exception
could also allow another origin to frame the app. This was not an
operator-selected first-party Flind integration.

The admin CSP also allowed loading a frame from the original vendor.
An unrelated inherited integration test incorrectly expected the
old vendor collector as the default CSP violation destination, even
though Wave 53 had removed that collection by default.

## Change

- The app's enforced frame-ancestors directive defaults to exactly
  the current document origin: frame-ancestors 'self'.
- app_frame_ancestor_sources admits no extra origins by default.
  The legacy vendor and preview iframe exceptions are not preserved.
- Embedded/shared/exporter pages retain their intentionally removed
  frame-ancestors directive where their routes explicitly require
  embedding; this change applies to the main application pages.
- The admin CSP continues to forbid being framed by anyone via
  frame-ancestors 'none', and removes its original-vendor frame-src
  exception in favor of 'self'.
- Update the inherited integration expectations for self-hosted
  framing and for no implicit donor CSP report collector.
- Targeted source/AST behavioral unit tests verify these safe defaults.

## Scope and qualifications

This does NOT remove other broad inherited CSP wildcards, nor certify
first-party external integrations, CSRF/HSTS/HTML assets, SDK event
ingestion, migrations or browser E2E. The app's framing behavior needs
future browser verification against real deployments.

No user-data change, deployment, public release, paid service or
global service modification. Repository stays private and inherited
GitHub Actions disabled. Mandatory attribution remains intact.

## Local validation

- Focused CSP/source tests 14/14 PASS.
- Tracked Flind Python source regressions plus Wave58 442/442 PASS.
- Untested broader Django browser CSP integration requires qualified backend.
