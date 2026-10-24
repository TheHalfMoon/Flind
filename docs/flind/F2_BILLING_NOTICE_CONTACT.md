# Flind F2 — billing banner support destination

The inherited project/billing notice logic routed the `contactSupport`
call-to-action directly to an unrelated product's sales inbox. That could
send Flind users' billing details to the wrong organization.

Now `buildBillingAlertAction` uses the same verified first-party
`flindPublicUrl('docs')` configuration as other Flind support surfaces.
The call-to-action is labeled **View support options** instead of promising
a sales or dedicated support service that does not exist.

If no operator-owned Flind documentation/support URL is configured,
the action is absent. Existing in-app billing navigation and engagement
tracking for valid actions are preserved.

The backend can still return separate `billingAlert.action` data; this
change does not qualify arbitrary backend-provided URLs. Other billing
pages still contain inherited sales URLs and subscription assertions
and must be audited in dedicated implementation/test waves.

Source regressions are in `tools/flind/test_billing_notice_contact.py`.
Full TypeScript/Jest/browser/payment integration are **NOT RUN** because
the connected desktop quota is unavailable and CI is intentionally
disabled. No external mailbox or legal policy was invented.

Release is **NO-GO** until the full billing/help UX, contract tests,
network egress and source identity gates pass. Do not publish.
