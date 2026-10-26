# Wave 155 — First complete original OAuth Vitest + TypeScript qualification

## Why this wave matters

Prior Flind OAuth migration waves 151–154 were validated by source-level Node24 harnesses but **the original service Vitest suite had not been run** because the Mac has an incomplete monorepo checkout and lacks workspace dependencies. This wave established a **narrow, no-cost, repeatable isolated service environment** without touching the user's original checkout or pulling the huge native/data stack.

Private GitHub `main` before the patch: `9a8c80ac395e8d5d2b531414d204d8fa1d36625d`.

## Environment and evidence

1. Read the exact original `services/oauth-proxy` tree from a partial Git clone. Out of 34 tracked files, 33 were locally accessible; restored the missing `vitest.config.mts` from the private GitHub Contents API. No global Git sparse expansion.
2. In an independent disposable `/tmp/flind-wave155-oauth-suite`, installed only `vitest@4.1.0`, `vite-tsconfig-paths@5.1.4`, `jose@6.2.3` using public npm, no scripts/audit, no paid infrastructure. Later added `typescript@5.9.3` and `@cloudflare/workers-types@4.20260120.0` for static type checking. Did **not** install the donor brand package or the full monorepo.
3. Baseline **original Vitest on actual main** under Node24, one worker: **101/103 PASS, 2 FAIL**. The failures were both isolated, reproducible:
   - `tests/security.test.ts`: an older cross-client security regression directly invoked the new Flind `handleAuthorize` signature without its required regional owner env.
   - `tests/fonts.test.ts`: Wave154 first-party picker switched to system fonts and no longer requested the original vendor WOFF2 faces, leaving a dead font import/route and a stale assertion.
4. Implemented targeted source fixes: pass owned synthetic Flind regions in the existing cross-client authorization-code isolation test; make the region pair validator fail closed on missing env (no direct-invocation TypeError); remove unused inherited WOFF2 Worker route and `src/handlers/fonts.ts`; remove unused original brand package dependency, Wrangler WOFF2 binary rule and Vitest font plugin; replace obsolete font test with `tests/picker.test.ts` asserting only Flind identity, no vendor URLs or font dependencies, and no exposed font route. Runtime gates for external OAuth remain unchanged and fail closed.
5. Copied the **exact Wave155 private PR-branch files** into the same disposable service fixture (26 available Git blobs + 7 freshly updated files from GitHub; removed deleted source/tests), preserving the isolated Node runtime and without modifying the original local checkout.
6. Executed the **complete original service test suite**, now with the first-party picker test, via:
   ```text
   node vitest/vitest.mjs run --maxWorkers 1 --no-file-parallelism --reporter=dot
   Test Files 9 passed (9)
   Tests      101 passed (101)
   Duration   1.70s
   exit code  0
   ```
   Every test ran in the original Vitest setup including OAuth security, cross-client state, token/reissue, discovery, authorization routing, registration, callback and global runtime admission.
7. Added real TypeScript static-checking packages in the disposable runner and executed `tsc --noEmit --project tsconfig.json` against all OAuth service sources/tests: **exit 0, no diagnostics**.

## Honest remaining release limits

**OAuth source regression and TS type checking are now qualified in a real test runner, but this is NOT a live OAuth or Flind product E2E proof.** Vitest uses mocked providers and in-memory KV; real issuer ownership, callback/PKCE, signing key rotation, refresh tokens, session cookies, Cloudflare runtime/KV and first-party network transactions remain unqualified. Wave151's full public OAuth runtime safety gate deliberately remains **closed** because `REGION_BASE_URLS`, token/JWKS/proxy/introspection paths still use inherited external origins.

The remaining work is to migrate the real token/JWKS/issuer/regional-proxy code together, re-run this now-available full Vitest suite and then qualify first-party OAuth over a disposable owner-controlled server. Django app-registry/migrations, production ingest and tenant-filtered Dashboard/browser E2E likewise remain issue #82 and still NO-GO. Source-wide identity/protocol migration remains issue #5.

No deploy/publish, repository remains private, inherited GitHub Actions disabled, no paid cloud, and legally required license/attribution records were not changed.
