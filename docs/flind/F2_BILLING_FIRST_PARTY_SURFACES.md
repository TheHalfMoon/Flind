# Flind F2 — billing error and credit panel first-party contact

Two billing-facing UI surfaces contained contact and marketing copy from the
source provider:

- The billing API error panel sent self-hosted users to another vendor's
  sales mailbox.
- The prepaid-credit panel promised Enterprise benefits including Slack
  support, training and merchandise that **have not been qualified or
  committed to by Flind**, along with the vendor's sales mailbox.

## Implementation

- Billing errors retain the existing in-app bug-report action when the
  instance reports cloud support. Other users get either an approved
  operator-configured Flind documentation link or a clear instruction to
  contact their Flind workspace administrator.
- Prepaid-credit panels show an optional **View Flind help** action only
  when a valid first-party docs destination is configured, with no
  unsupported Enterprise claims.
- Payment processing, billing calculation, invoice URL, credit purchase,
  modal actions and account data contracts are unchanged.

The link uses `flindPublicUrl('docs')`; no fake email address is invented.
A real Flind billing/support channel and its legal obligations remain to
be established before a public paid offering.

## Verification and limitations

`tools/flind/test_billing_first_party_surfaces.py` contains four
source regressions covering external email removal, absence of unsupported
claims, preservation of in-app bug reporting and purchase actions.

Actual Python test execution, frontend compiler, Jest, payment gateway
sandbox tests, browser click-through and end-to-end billing flows remain
**NOT RUN** because connected desktop execution quota was reached and
GitHub Actions are disabled.

Other billing and sales surfaces, including enterprise enrollment,
subscription management and unsubscribe flows, still need independent
audits. Flind remains PRIVATE and release **NO-GO**. Do not publish.
