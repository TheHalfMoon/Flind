# Provenance

Vendored from the npm package `@posthog/siphash` 1.1.3 (PostHog's fork of Frank Denis's
[siphash-js](https://github.com/jedisct1/siphash-js), which adds `siphash-double`), as part of Flind's rename of
PostHog's published packages (`flind/rename/PLAN.md`, stage 3). The library code is unchanged; only the package name and
metadata differ. The published `test/index.js` (a vector printer that required modules the package does not ship)
is replaced by `test/flind.test.js`, which checks the 150 SipHash-2-4 vectors from it and `siphash-double`. It stays under its BSD-2-Clause license and copyright (`LICENSE`).
