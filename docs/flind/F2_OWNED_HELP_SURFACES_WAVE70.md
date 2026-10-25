# Wave 70 — Product-tour and analytics help URLs must be Flind-owned

## Changes
- Four Product Tours targeting tooltips use the existing
  `flindPublicUrl('docs')` allowlist and no inherited vendor links.
  Dynamic text matching instructions now correctly use the Flind name.
- The Web Analytics path-cleaning tooltip retains its in-app settings
  navigation. Its external docs link is shown only when the operator
  configures a first-party HTTPS documentation URL.
- The Experiments wizard omits the entire optional documentation prompt
  without a configured Flind docs site, rather than leaving a dead link.

No replacement domain, route or website is invented, and no blanket
source rename modifies third-party dependencies or legal attributions.

## Evidence, October 25 2026
- Six direct inherited help links removed across three production TSX
  components.
- 3/3 TypeScript+JSX files pass Babel parser syntax checks.
- 10/10 focused Wave 69 + Wave 70 regression tests pass.
- Git whitespace checks pass.
- Full browser click paths, actual frontend typecheck, Vite production
  build and network egress are still NOT qualified because the isolated
  workspace does not have the full dependency graph installed.

## Release status
Issues #24 (remaining documentation URLs), #5 (complete source/binary
identity), #3 (upstream cloud egress), #82 (backend/schema+SDK pipeline)
remain open until independently tested. The repository remains private,
inherited GitHub Actions disabled, no deployment, publication, paid
services, or stripping of legally mandatory attribution.
