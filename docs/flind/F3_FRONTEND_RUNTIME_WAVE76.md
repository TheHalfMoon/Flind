# Wave 76 — Real JavaScript runtime, Jest and first-party OAuth boundary

## Locally qualified toolchain (2026-10-25)

The authorized Mac had Node 26 and pnpm 12, while Flind's repository
requires `node >=24 <25` and `pnpm@11.28.5`. A separate **official**
Node.js 24.22.1 LTS Apple Silicon archive was downloaded into
`/tmp/flind-wave76-node` (no system Node replacement), with its
SHA-256 verified against the matching official Node.js 24.22.1
`SHASUMS256.txt`:

```
node-v24.22.1-darwin-arm64.tar.xz
654ba79de6155647e22321932b45f2a1ccb705976cc337c9b8e278beb085a628
```

With that Node 24 in `PATH`, Corepack resolved the repository's exact
`pnpm@11.28.5`. In a **separate sparse Git worktree**, the frontend
and dependent workspaces successfully installed **2,344 packages**
using a frozen lockfile with npm's public registry. Installation had
`--ignore-scripts`, protected a 12-GiB disk floor, and did not touch
the main or another agent's source worktree. No paid services used.
Root build-time dependencies were installed separately.

## Reproduced bug in frontend Jest

The stock frontend Jest configuration uses Sucrase to produce CommonJS,
but Sucrase leaves `import.meta.env` intact. A genuine LemonToast
test would not even start because the indirectly imported first-party
OAuth module evaluated `import.meta.env` in Jest/CJS:

```
SyntaxError: Cannot use 'import.meta' outside a module
```

Wave 76 adds a **Jest-only**, syntax-aware Sucrase wrapper. It uses
the already pinned TypeScript dependency to replace *actual parsed*
`import.meta.env` expressions **only** in six first-party Flind
browser-config source modules with an empty test environment. This
fails closed: tests never load machine/cloud OAuth IDs, URLs or support
mailboxes implicitly. It does not modify production bundling, runtime
environment variables, source strings/comments, `import.meta.url`,
or displayed Vite SDK setup instructions. The Jest dependency extractor
uses the identical wrapper to keep the import graph coherent.

## Real OAuth bug repaired

With proper Jest transformation, targeted OAuth tests uncovered a real
security condition: `configuredOAuthRegion()` accepted a configured
`https://host:8443` address because `URL.origin` includes the port
and therefore equalled the original string. Now an **explicit nondefault
port is rejected** along with HTTP, paths and embedded user info.
This is a production validation change, not just a test change.

## Executed evidence

- 6/6 exact-source Node.js AST-transform, stylesheet and product-owner guardrail tests PASS.
- **151/151 focused actual frontend Jest tests PASS** across
  `LemonToast`, `oauthClient`, `flindRegionHosts`,
  `flindPublicLinks` in 8 passing suites (Node 24/pnpm 11,
  isolated worktree, Jest --runInBand --no-cache).
- Jest previously failed before running tests due to import.meta; after
  the patch all four suites now execute and pass.
- Initial genuine frontend `tsgo --noEmit --checkers 1` did start
  correctly using pinned TypeScript-Go 7.0 preview, but did **not**
  finish within the resource-bounded 240 seconds. It emitted no
  diagnostics before the time limit, so neither a complete typecheck
  success nor error-free full project is claimed.
- **Actual build:products PASS**. The first full production build exposed
  missing @flind/quill output because the Quill workspace still targeted
  inherited package names, which was fixed; full Quill Vite + CSS build
  PASS (8 scoped workspace projects). @flind/logicvm local Parcel build PASS.
- Additional full-build errors caused by inherited stylesheet paths and
  removed upstream cloud exports were repaired in first-party Flind
  sources; targeted Jest tests prove the admin-region and same-origin
  image behavior. The final full production esbuild run proceeded without
  new module-resolution errors and independently built Toolbar, Render
  Query, Infrastructure Admin and multiple Monaco/other workers, but
  was terminated by the predeclared **11 GiB available-disk safety guard**
  after 115 seconds. **Whole-app bundle was NOT completed / not qualified**.
- Full TypeScript-Go compilation was bounded at 240 seconds with no
  result; frontend typecheck remains UNQUALIFIED, not a pass or a code error.
- Full Jest suite, end-to-end browser and network-egress qualification
  remain **NOT QUALIFIED**.
  Lockfile, repo publicity, deployment and licensing policy unchanged.

## Reproduction

Use a separate, full-enough Flind worktree with exact Node/pnpm versions:

```sh
corepack pnpm --filter '@flind/frontend...' install --frozen-lockfile --ignore-scripts
corepack pnpm --filter . install --frozen-lockfile --ignore-scripts
node --test tools/flind/test_jest_transform_wave76.cjs
corepack pnpm --filter '@flind/frontend' exec jest --runInBand \
  --runTestsByPath src/lib/lemon-ui/LemonToast/LemonToast.test.tsx \
  src/lib/oauth/oauthClient.test.ts \
  src/lib/flindRegionHosts.test.ts \
  src/lib/flindPublicLinks.test.ts --no-cache
```

No publication, hosting/deployment, paid cloud, or legal attribution
removal. Repository private and inherited GitHub Actions disabled.
Issues #3/#18/#24/#82 and whole-product release gate remain open.
