# Wave 32 — Atomic CLI device-flow claims and one-time credentials

## Threat model and observed defect

The backend CLI authorization implementation used a read-check-write
sequence to mint personal API keys and a read-delete sequence to deliver
the authorized key. Previous tests only verified sequential retries.
Simultaneous requests could read the same pending or authorized state before
one request had updated/deleted the cache value. These are not one-time
OAuth device authorization semantics.

The short human-readable user code also used unconditional cache.set for
the reverse lookup. A collision could silently replace the lookup mapping
of an already pending device.

## Implementation

1. After validating scopes, project and team authorization, reserve a
   per-device authorization claim via atomic cache.add before minting a PAT.
   Keep a successful claim through the original device code lifetime.
   A competing consent receives an already-authorizing or already-authorized
   error rather than minting again.
2. Release the claim if minting itself fails. A later error after minting
   leaves the claim held to avoid accidentally issuing duplicate credentials.
3. On the authorized poll branch, reserve a separate per-device delivery
   claim via cache.add before constructing the response. Competing polls
   receive expired_token (400) without a key.
4. Reserve each user code via cache.add, retrying at most eight generated
   candidates. On exhaustion return 503; never overwrite another
   device's mapping. On device-cache write failure release the mapping.
5. Preserve existing CLI public API routes, payload shapes and scopes.

## Behavioral validation

The dependency-free tests execute actual Python AST methods extracted
from posthog/api/cli_auth.py with a thread-safe stand-in for cache.add.

- Sixteen simultaneous authorizers: exactly one key minted.
- Sixteen simultaneous polls: exactly one credential delivery.
- Failed mint releases the claim, user-code collision preserves its first
  owner, and exhausted attempts fail without corruption.
- Four Django API regression tests added for eventual integrated running,
  including collision, exhausted allocation and two claimed-state checks.
- Python syntax and full Flind Python source regression suite are required
  before merge.

## Boundaries and caveats

This does not constitute Redis/Django/Postgres E2E qualification.
Production cache configuration uses Redis, but live multi-instance
atomic behavior and failure injection remain to be verified.
Atomic cache.add cannot provide a transaction with the database or network;
after an unknown mint/response failure, reconciliation or explicit PAT
revocation may be required. The implementation intentionally refuses
a second delivery when the first may have succeeded.

No real credentials, server startup, external API calls, deployment or
publishing. Repository private; inherited GitHub Actions disabled.
Release remains NO-GO.
