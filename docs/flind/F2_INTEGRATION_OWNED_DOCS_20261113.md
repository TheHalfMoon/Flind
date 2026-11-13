# Integration documentation and marketing asset isolation

Scope: first-party help links for GitHub, GitLab, Jira, Linear, Slack,
and Twilio integration configuration. No OAuth or API endpoint changes.

## Change

- Five integration detail pages use `flindDocsUrl(relativePath) ?? undefined`.
  The page's existing conditional "Learn more" link remains visible only
  if the operator configures an exact Flind-owned HTTPS documentation root.
- Slack channel setup and Twilio phone-number picker retain the original
  functional configuration actions, but link to the same optional first-party
  documentation root. Absent docs show the error explanation without a link.
- GitHub integration description retains an in-app route to Slack and a
  textual Desktop reference, but no longer advertises a donor desktop URL.
- Slack detail no longer fetches a marketing banner from a donor-operated
  Cloudinary account. Slack's own installer, authentication and permissions
  remain intact, because those are genuine third-party integration endpoints.

## Verification

The five dependency-free tests in
`frontend/bin/flind-integration-docs-owned.test.mjs` assert first-party
URL derivation, conditional rendering, retained integration setup actions,
and absence of inherited provider doc links. Exact-head GitHub tests also
run frontend Jest, TypeScript diff regression and the rename ratchet.

The test does **not** assert the configured Flind documentation pages have
been published or that user-initiated third-party provider connections are
functional. Those still need integration E2E, app configuration and network
egress review. Preserved legal attribution is unaffected.

No release, tag, package publication, hosted product or vendor service
without the founder's explicit `GREEN LIGHT FLIND`.
