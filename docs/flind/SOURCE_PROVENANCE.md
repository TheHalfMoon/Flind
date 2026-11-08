# Flind source provenance and licensing

Recorded 2026-11-08.

## Source

Flind is derived from the PostHog monorepo. The donor licence files are kept unchanged:

- `LICENSE`: MIT Expat for everything outside `ee/`, copyright PostHog Inc.
- `ee/LICENSE`: PostHog Enterprise licence for content under `ee/`.

## Owner attestation

The repository owner states that they hold full legal permission to copy, modify and rename the PostHog source, including the `ee/` directory, for Flind. The owner has chosen not to share the permission document. This record is the owner's attestation: the engineering agent has not seen or verified the grant.

On that basis, `ee/` is kept and rebranded together with the rest of the source.

## Obligations kept regardless

- The copyright and permission notices in `LICENSE` and `ee/LICENSE` stay in the repository and in any distribution (MIT attribution condition).
- Third-party components keep their own licences.
- Rebranding covers the product name, logos and user-facing text, because the MIT licence grants no trademark rights. Compatibility-critical identifiers (Python package paths, SDK names, wire formats, historical migrations) may keep donor names; each one is documented in the brand guard allowlist.

## Publication

No release, image, package or public deployment is authorised. Publication needs the owner's explicit "GREEN LIGHT FLIND".
