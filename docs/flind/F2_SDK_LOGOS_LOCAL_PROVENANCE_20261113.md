# First-party-hosted SDK selection logos

Status: **37 external SDK image references replaced with 35 original
deduplicated locally bundled images**; exact-head frontend Jest/TypeScript
and CI are required before merging this source change.

## Privacy and product fidelity

Flind previously offered first-party-or-hidden SDK documentation but
the adjacent SDK selector still loaded logos directly from a legacy
Cloudinary media account. An ordinary visit to the SDK grid could
contact that external host before the user selected any SDK.

This PR vendors the same original visible icon assets into
`frontend/src/scenes/onboarding/shared/logos/vendor/` and imports them
at frontend build time. Each catalog entry still has the same SDK key,
display name, tags, recommendations and document destination. The
35 unique images cover 37 image references in the 93-item catalog
(duplicate Vercel images are reused). There is no runtime URL or
external CDN dependency in the catalog, and images are provided from
the app's regular static asset build. The static assets total around
247 KiB including the provenance manifest.

The pinned `SOURCES.json` records each original asset URL, the
downloaded SHA-256, detected content format and byte size. This file
is for provenance, **not** imported into the browser. Files received
as WebP, despite original URLs ending in PNG due Cloudinary format
negotiation, retain their actual `.webp` extension in the repo. SVGs
were parsed and checked to reject scripts, event attributes, HTML
foreign objects, remote hrefs, XML entities and remote stylesheet URLs.
All assets are fetched **only during this one-time development import**,
not at application runtime.

### Compliance and limits

Vendor/project/provider logos remain third-party visual marks and
are **not** claimed as original Flind artwork. Keep existing required
source licenses and Notices and review trademark and image-source
usage as part of any future public release. Source URL provenance is
retained outside the product UI. Logos may be refreshed only after a
new content, safety, provenance and checksum review.

This scope does **not** prove zero external requests from every
Flind screen or from third-party SDK runtime code; the entire frontend
still needs a real browser network-egress campaign. The locally
bundled images are not downloaded through runtime JavaScript and no
new tracking or API calls are introduced.

## Reproducible checks

`node --test frontend/bin/flind-sdk-local-logo-assets.test.mjs`
validates all 93 entries, all 37 formerly remote catalog references,
all 35 assets against their source hash, size and actual image format,
no active/external SVG resources and existing SDK UI renderers. Full
frontend Jest and TypeScript compilation on the exact branch head
are required before merge.

No release, installer, public SDK package, GitHub tag or deployment
until explicit `GREEN LIGHT FLIND`.
