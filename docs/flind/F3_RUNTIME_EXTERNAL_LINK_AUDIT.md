# Flind — runtime source external-destination inventory

The broad `brand_audit.py` measures inherited identity in tracked files but does not
separate executable source destinations from test fixtures, docs and legal provenance.
This read-only, zero-dependency audit focuses on **literal potential outbound destinations**.

## Run

```bash
python3 tools/flind/check_external_links.py --sample-limit 150 > flind-external-links.json
python3 tools/flind/check_external_links.py --strict > flind-external-links-strict.json
PYTHONPATH=. python3 -m unittest tools.flind.test_external_links -v
```

The default command emits JSON and exits successfully so the remaining migration
inventory can be read. `--strict` exits **2** if any matching destinations or
uninspected runtime-source files remain; it should currently be treated as a
release blocker, **not** an instruction to enable CI or publish the product.

The scanner uses `git ls-files`, reads likely runtime `*.ts`, `*.tsx`, `*.js`,
`*.py`, `*.html`, `*.ejs`, `*.go`, `*.rs` and other source types, and reports:

- Candidate files scanned / files not scanned because of size/read failures
- Number of source files containing inherited destinations
- Literal `http://`, `https://`, `mailto:` and bare hostname references
  to the inherited provider and its status service
- Example source paths, 1-indexed line numbers and matched values
- Counts by top-level source area and link type

The scanner excludes files under docs, tools, recognized test/fixture/generated
paths and binary/other extensions, so **legal attribution and test fixtures are
not automatically edited or misreported as live product navigation**. Keep
required LICENSE/NOTICE files and factual third-party credits intact.

## What it does *not* prove

The result is a **static review queue**, not a browser network trace or
verification that a link is reachable. A hit could be a comment or dormant
feature; an actual egress path could be generated dynamically, represented by
an IP address, use an unrecognized provider or exist in a built package.
Excluded/test/source-oversize files remain visible as scope limitations.

Do **not** replace all matches mechanically: distinguish Flind-owned operator
routes, explicit third-party integrations, billing and OAuth contracts,
migration fixtures, and network-dependent services. Preserve functioning
features; redirect only to verified Flind-owned destinations and hide
unconfigured features rather than inventing URLs.

## Required release sequence

1. Run the literal destination scanner and the separate full source
   `brand_audit.py --strict`; reconcile their inventories.
2. Investigate each high-risk source destination and migrate in functional
   testable batches (login, onboarding, payment, SDK ingestion, etc.).
3. Install/build frontend and backend, run unit/integration and browser
   end-to-end tests, check credential/session handling and database migrations.
4. Trace real HTTP/DNS egress on clean installs across supported OSes.
5. Recheck third-party licenses and packaging, and publish only after
   independent gates genuinely pass.

**Release remains NO-GO.** No GitHub Actions were enabled; no deployment is made.
