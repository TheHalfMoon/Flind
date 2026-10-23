# Flind — same-origin trusted content boundary (F2 Wave 5)

The inherited rich-content URL trust check accepted URLs from an unrelated
provider's cloud domains as safe to automatically render or linkify.

## Implementation

- Replace the old URL predicate with `isTrustedFlindUrl`.
- Trusted URLs must match `window.location.origin` exactly, including protocol
  and port. Relative URLs resolve against this Flind origin.
- Disallow `data:`, `blob:`, `javascript:`, sibling subdomains, lookalikes,
  off-origin absolute links and cross-port URLs.
- Route both LemonMarkdown trusted-image handling and error-detail link
  rendering through this one predicate.

## Verification

- Three new dependency-free static gates PASS.
- TypeScript 5.9.3-transpiled predicate executed in Node, with 11 positive and
  negative origin cases PASS.
- `git diff --check` PASS.

## Open gates

- Full React component/browser tests and complete TypeScript typecheck NOT RUN.
- Audit other outbound media and link rendering consumers.
- Migrate SDKs, backend modules and protocols, and pass source-wide/binary
  zero-identity and network egress release checks.
