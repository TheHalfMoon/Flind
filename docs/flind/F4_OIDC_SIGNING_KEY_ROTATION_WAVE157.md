# Wave 157 — Correct OIDC signing-key cache identity during live rotation

## Production identity/security defect

The OAuth OIDC proxy caches imported private keys for performance while signing reissued ID tokens and publishing proxy JWKS. The prior `keyCache` in `src/lib/idtoken.ts` was a `Map<KeySlot, Promise<ProxyKey>>` and keyed only by `active`/`inactive_1`/`inactive_2`.

When the operator changed `OIDC_SIGNING_KEY` or an inactive rotation key while the same Worker isolate was alive, `loadKey()` could return the cached **previous key** for the unchanged slot. Token signatures and published `kid` would therefore be inconsistent with the currently configured private key, potentially breaking key rotation or publishing retired keys as active.

## Production fix

The per-slot cache now stores both the **normalized PEM value** and pending `Promise<ProxyKey>`. `loadKey(slot,pem)` reuses the cached import only when the current, normalized PEM matches. A changed key immediately creates a fresh `kid`/public JWK and private CryptoKey for the slot. This retains deduplicated parsing for the same exact key and supports PEMs containing literal or escaped newlines.

This wave is limited to the **local private signing-key import cache**; it does not change the regional JWKS backend origins or Cloudflare Worker egress gate. The next step must separately migrate upstream issuer/JWKS identity with proper origin-scoped cache invalidation.

## Executed evidence (2026-10-26)

Updated actual source `services/oauth-proxy/src/lib/idtoken.ts` and added `tests/signing-key-rotation.test.ts` using real JOSE RS256-generated RSA PKCS#8 keypairs and actual `proxyJwks()` calls **within the same test worker process**:

1. Active-key PEM replacement changes the public key and `kid`, and switching back recovers the original key identity.
2. Inactive-key PEM replacement changes the inactive `kid` while the active key remains unchanged.
3. Escaped newlines normalize identically, and absent keys publish no proxy JWKs.

The isolated, original full OAuth test environment was already qualified in Wave156, and for Wave157 the exact branch's idtoken.ts and new test source were loaded into this fixture. **Vitest 11/11 test files PASS, 111/111 tests PASS (exit 0; 2.31 seconds)**. **`tsc --noEmit --project tsconfig.json` PASS (exit 0, zero diagnostics)**.

No real user account, OAuth server, private production key, Cloudflare KV or external request was involved. Actual live OIDC/PKCE, regional issuer verification/keys, signing-key rollback, network outage and key-rotation release test remain future gates. Repo private, inherited Actions disabled, no publish/deploy/paid cloud, required legal attribution preserved.
