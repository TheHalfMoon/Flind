import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(
  new URL("../../products/desktop/packages/core/src/oauth/oauth.ts", import.meta.url),
  "utf8",
);
const cases = readFileSync(
  new URL("../../products/desktop/packages/core/src/oauth/oauth.test.ts", import.meta.url),
  "utf8",
);

test("desktop OAuth credential POSTs refuse redirects", () => {
  const matches = source.match(/redirect: "error"/g) ?? [];
  assert.ok(matches.length >= 2, "Both code exchange and token refresh must deny redirects");
  assert.match(source, /response\.status >= 300 && response\.status < 400/);
  assert.match(source, /prohibited redirect/);
  assert.match(cases, /\[301, 302, 303, 307, 308\]/);
  assert.match(cases, /synthetic-refresh/);
  assert.match(cases, /synthetic-code/);
});
