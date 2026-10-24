# Wave 42 — Desktop inherited legal acceptance containment

## What was inherited

The Desktop consent panel actively accepted the original vendor's AI/data
processing and Desktop beta terms through backend mutation endpoints. It
displayed provider-specific subprocessors, an unsupported promise about AI
training, statements about HIPAA/PHI and another organization's BAA,
and copied direct links to that company's account settings. Rebranding
those claims as Flind would give users inaccurate legal disclosures.

## What changed

- Replace the interactive vendor approval decisions with read-only,
  first-party legal qualification status. There are no approval controls,
  inherited vendor privacy/subprocessor links, or copied account-setting links.
- Leave Refresh functional; it invokes the existing consent query retry
  without writing consent flags, and errors remain visible.
- Keep AI and beta outstanding requirements distinct for admins and users.
- Keep the onboarding Next button disabled whenever consent is loading,
  failed, or unsatisfied. Do not initialize acceptance flags to true.
- Do not change backend API/database schemas or delete historical consent
  records. Those remain compatibility state, not Flind consent authority.

## Evidence

- Real React/Vitest checks assert there are no acceptance actions,
  no external links, correct distinct requirements, working retry/error
  behavior and no inherited provider/PHI claims.
- Original ConsentScreen test still passes.
- Source guards block reintroduction of mutation methods and vendor SSO URLs.
- Flind Python source regressions: **317/317 PASS**.
- Full @flind/ui TypeScript validation: **PASS, zero errors** on rerun.
  The initial attempt caught an obsolete Back-button submitting-state
  reference; this was corrected rather than suppressed.

## Outstanding legal/product limitations

Read-only panel changes do not constitute legal review. Previously stored
accepted flags could permit onboarding through other screens: complete
first-party consent storage, all first-run gate paths, policy/subprocessor
declarations and backend integration E2E remain release blockers.
No publication/deployment, private repo, inherited GitHub Actions disabled,
and required third-party notices preserved.
