# Wave 141 — Flind first-party Python distribution identity

## Identity requirement

Flind must own the first-party Python package metadata. Previously the root
`pyproject.toml` declared `[project].name = "posthog"` and the frozen
`uv.lock` still listed a virtual root package, workspace member,
dependency-group markers and group conflicts in the old name.

The root distribution is now **`flind`**. Regenerated the frozen lock with
the already qualified free `uv 0.13.5`, keeping the existing
`==3.14.7` Python patch and **all 623 package versions, dependency metadata,
wheel hashes and upstream URLs unchanged**. Six pre-existing NVIDIA cross-platform
dependency environment markers were preserved verbatim after the latest uv solver
offered broader markers; identity rebranding is not permission to change
platform requirements. Root dependency count remains 202 and the local project
remains version 0.0.0. The two incompatible `sentiment` and
`inbox-ranking` dependency groups now resolve as Flind groups.

## Executed proof on Mac (isolated source worktree)

- `uv lock --check --offline --python <exact Python 3.14.7>`: PASS
- `uv sync --frozen --no-dev --no-default-groups --no-install-project
  --dry-run --python <exact Python 3.14.7>`: 451 packages checked,
  **no changes** to the previously installed frozen production environment
- Parsed old and new uv.lock TOML entries and normalized only the first-party
  project name / generated group markers: **623/623 package entries otherwise
  identical** and all four known NVIDIA dependency groups preserved
- `tools/flind/test_flind_distribution_identity_wave141.py`: unit checks for
  project identity, root lock metadata, generated dependency conflict groups,
  Python patch consistency, and historical notices

## Explicit scope boundary

The Python *distribution* name is Flind. This wave **does not** rename the
`posthog` Python import namespace, Django app labels/migrations or stored
feature flags. Those are live schema/protocol identifiers and require a
coordinated, verified compatibility migration rather than global text
replacement. Legally required copyright and third-party attributions
remain in LICENSE/NOTICE files. The remaining source-identity audit is tracked
in #5 and real backend E2E in #82.

Repository private, inherited Actions disabled, no release/publishing/deploy,
no paid services. This is an identity milestone, not app release qualification.
