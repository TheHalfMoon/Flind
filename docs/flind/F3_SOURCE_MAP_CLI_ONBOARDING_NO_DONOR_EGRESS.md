# Flind first-party source-map installer safety gate

Status: **draft; exact-head full frontend Jest/TypeScript/migrations/ratchet
are pending.** This is a fail-closed onboarding UI restriction, not the
release of a usable Flind source-map CLI.

## Security and correctness problem

The original error-tracking source-map wizard displayed a one-line shell
installer from `download.posthog.com/cli`, followed by a CLI login and
source-map upload command. The inherited CLI crate/release configuration
in `cli/` is not yet Flind-owned or distribution-qualified; its default
host and existing download/update URLs are associated with the donor.
Source maps and native iOS dSYM files may contain application-private
code, identifiers and debugging information.

Showing these commands as *Flind* setup could send credentials, source
maps and symbols to a service not configured or owned by the operator.
Renaming the public CLI package in text would not make the binary,
installer or upload destination safe.

## Scoped fail-closed change

The step still offers its two currently supported non-upload choices:
"Unminified code" and "Public source maps". They remain selectable, and
the optional source-map step can still be skipped. Existing symbol-set
status and account API key modal remain available.

The "Private source maps" option now **explicitly states** that Flind's
owned CLI is not qualified and that installation, login and upload
commands are withheld. The prior automatic Next.js, Nuxt and iOS
uploader configuration cards are no longer rendered from this wizard.
The wizard does not invoke the inherited installer or provide commands
for an unqualified upload binary.

This intentionally sacrifices one unverified onboarding route rather
than risk claiming a Flind-owned installer exists. It does not delete
debug symbol data, mutate existing project settings or turn off already
configured server-side source-map APIs. Previously deployed third-party
CLI scripts remain outside the scope of this UI change.

The source code of older automated uploader example components still
exists for future audited first-party migration, but no longer has an
active import or render path through this wizard. They must not be
reactivated until qualified.

## Release requirements

Before reopening these instructions, the owner must implement and
qualify all of:

- an independently branded, versioned, reproducible CLI with preserved
  required source license/NOTICE and no hidden donor telemetry;
- a verified first-party HTTPS/default-deny upload host, credential
  confinement and authenticated tenant/project permission checks;
- a trustworthy owned download endpoint, checksums/provenance,
  platform-specific installer validation, update/rollback path;
- actual synthetic source-map and iOS dSYM ingestion into a local Flind
  server, negative cross-tenant access, failure/retry and retention QA;
- CI on each platform, explicit user approval for private source-code
  upload, and no production external egress without consent.

`node --test frontend/bin/flind-source-map-onboarding-safe.test.mjs`
provides a dependency-free regression for the scoped wizard. It does
not prove build/install/runtime acceptance. The full frontend
Jest/TypeScript/migration and rename gates are mandatory before merge.

Release stays **NO-GO**, and no public tag, package, installer, hosted
application or binary distribution is authorized without founder
`GREEN LIGHT FLIND`.
