# F1 Wave 4 — Flind primary browser and PWA assets

**Design status:** a temporary Flind-owned wordmark and icon, **not** the final founder-approved identity.

## Implementation

- Added `frontend/public/flind-icon.svg`, `flind-logo.svg` and `flind-logo.png`.
- Replaced the *contents* of inherited browser favicons, Apple icon, PWA 192/512 icons and Safari pinned-tab icon with first-party Flind artwork.
- Updated `site.webmanifest` colors, description and cache-busted image URLs.
- Updated HTML favicon/manifest cache versions and Safari mask color.
- Updated a real experiment notification URL to `/static/flind-icon.svg`.
- Kept transitional legacy static-url aliases whose **image bytes now equal** the new Flind files, so callers awaiting migration do not display inherited logos.
- Added `tools/flind/generate_brand_assets.py` to reproduce PNG, ICO and SVG assets from editable definitions. Pillow and a supported host font are only needed when regenerating assets, not at runtime.

## Verification

- 33 lightweight standard-library tests PASS (including six new asset tests).
- 8 original identity assertions PASS.
- All generated PNGs/ICOs were opened and verified using Pillow in a standalone verification run.
- Python compilation and `git diff --check` PASS.

## Outstanding (release-blocking)

- Product-wide icon and illustration crawl, with screenshots on desktop/mobile.
- Hundreds of imported logos, mascots and secondary illustrations may still be present.
- Legacy compatibility filenames remain until all callers move to Flind URLs.
- Final approved visual design, theme review, contrast, accessible assets and E2E browser inspection.
- SDK/import/path/schema rebranding and binary release scan. The strict source-wide zero-identity gate still fails.

No release or publication has been performed.
