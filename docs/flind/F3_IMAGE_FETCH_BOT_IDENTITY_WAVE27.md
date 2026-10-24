# F3 Wave 27 — independent session-replay image bot identity

## Risk

Both the copied ML mirror and AI-research image-fetch lanes identified outbound
requests as the original vendor's image fetcher, claimed the original vendor's
US cloud Referer, and embedded its signature-agent key directory in Ed25519
Web Bot Auth signatures. This was neither independent Flind branding nor a
legitimate signing identity for a new Flind deployment.

## Source implementation

- Share the FlindImageFetcherBot name and request headers through one owned
  session-replay identity module. Avoid duplicating policy in two fetchers.
- Remove inherited Referer and upstream help URL from the user-agent default.
- Permit an explicitly configured FLIND_IMAGE_FETCHER_IDENTITY_ORIGIN, requiring
  an HTTPS origin without URL credentials, paths, query, fragment, or legacy
  vendor cloud domain. Reject equivalents with trailing DNS root dots.
- Require that same explicit origin to construct the Web Bot Auth
  signature-agent directory URL. Fail closed if absent; no fake Flind
  signature directory is asserted to exist.
- Preserve Ed25519 signatures, the Web Bot Auth wire shape, key rotation and
  existing robots.txt/x-robots-tag policy logic; adapt test bot-name fixtures.
- Two copied image-fetch lanes now use one source of truth.

## Qualification

- Actual transpiled TypeScript signer code run under Node 24 and verified
  using real Ed25519 keypairs and node:crypto.verify: 20/20 behavioral checks
  passed across both lanes, including changed-URL signature failure and
  rejection of unconfigured/upstream identity origins.
- Source regression tests ensure both lanes use Flind identity and forbid the
  legacy signature directory.
- TS source/test parser covers 12 touched TypeScript files with zero syntax
  errors.
- Full Flind Python regression suite: 256/256 PASS after all edits.
- The repository's original Jest image-fetcher and configuration-policy test
  suites were NOT executed: full Node ingestion workspace deps are not present.

## Release caveats

This changes the bot user-agent and opt-out scoping. External image hosts may
have previously allowlisted the inherited bot and will need a new Flind
allowlist. Flind has not created the required public .well-known signing key
directory. In deployments that provide Web Bot Auth signing keys but no Flind
identity origin, signer creation now fails rather than forging a third-party
identity. Live fetch/robots/redirect/egress and product end-to-end tests remain
unqualified. No external traffic was sent during cryptographic tests.

Repository remains private; GitHub Actions disabled; do not publish, deploy
or claim release readiness. Preserve mandatory upstream MIT/legal notices.
