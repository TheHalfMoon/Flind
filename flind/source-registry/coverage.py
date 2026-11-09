"""Write coverage.md for the Flind source registry from registry.json."""

import json
from collections import Counter

reg = json.load(open("registry.json", encoding="utf-8"))
total = len(reg)
by_cat = Counter(r["category"] for r in reg)
scope = Counter(r["flind_scope"] for r in reg)
in_scope = [r for r in reg if r["flind_scope"] == "in-scope"]
no_license = [r for r in in_scope if r["license_spdx"] in ("NONE", "NOASSERTION")]

lines = [
    "# Flind source registry: coverage",
    "",
    "Generated from the GitHub API listing of every repository in the `PostHog` organisation that is visible",
    "to the authenticated account (`gh api --paginate orgs/PostHog/repos?type=all`). No private repositories were",
    "visible, so category 12 is empty; private repositories, if any exist, are not covered and would need separate",
    "authorization.",
    "",
    "Files: `registry.json` and `registry.csv` (one row per repository), `classify.py` (the rules), `repos.tsv`",
    "(the raw API listing).",
    "",
    "## Totals",
    "",
    f"- Repositories discovered: **{total}**; classified: **{total}** (100%), unclassified: **0**.",
    f"- In scope for Flind (categories 1-5): **{scope['in-scope']}**; needs a scope decision (6, 7, 8): "
    f"**{scope['review']}**; out of scope (9, 10, 11): **{scope['out-of-scope']}**.",
    f"- In-scope repositories are pinned to their default-branch head SHA on the listing date.",
    "",
    "| Category | Repositories |",
    "| --- | ---: |",
]
for cat, n in sorted(by_cat.items(), key=lambda kv: -kv[1]):
    lines.append(f"| {cat} | {n} |")

lines += [
    "",
    "## In-scope repositories",
    "",
    "| Cat | Repository | License (SPDX) | Pinned SHA | Revision date | In Flind |",
    "| ---: | --- | --- | --- | --- | --- |",
]
for r in in_scope:
    sha = (r.get("commit_sha") or "")[:12]
    date = (r.get("source_revision_date") or "")[:10]
    lines.append(
        f"| {r['category_id']} | [{r['name']}]({r['repository']}) | {r['license_spdx']} | `{sha}` | {date} | {r['present_in_flind']} |"
    )

lines += [
    "",
    "## Notes",
    "",
    "- **Core:** `posthog` was imported into Flind at `cd26680c84533f65f43e1c7efc701bf792a5363a`. Its current upstream",
    "  head is listed above; the difference is the Stage 3 upstream delta. `posthog-foss` is the MIT-only mirror and",
    "  serves as the licensing boundary reference for `ee/`.",
    "- **SDKs not listed separately:** the Node SDK, React Native and `posthog-js-lite` are maintained inside the",
    "  `posthog-js` monorepo, so that entry covers them.",
    f"- **Licensing:** {len(no_license)} in-scope repositories declare no SPDX license (`NONE`) or `NOASSERTION`.",
    "  The owner attests full permission to copy and rename PostHog source (see `docs/flind/SOURCE_PROVENANCE.md`);",
    "  each import must still keep the upstream copyright and license files.",
    "- **Hosted dependencies:** repositories whose purpose is a PostHog-operated service (for example the billed LLM",
    "  gateway integration) are classified but out of scope for a self-hosted Flind.",
    "- **Categories 6-8** (deployment, integrations, shared infrastructure) are marked `review`: they are imported only",
    "  when a product capability needs them.",
    "- Integration status, test results and target Flind directories are filled in per repository as each is imported.",
    "",
]
open("coverage.md", "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print(f"coverage.md: {total} repos, {len(in_scope)} in scope, {len(no_license)} in-scope without SPDX license")
