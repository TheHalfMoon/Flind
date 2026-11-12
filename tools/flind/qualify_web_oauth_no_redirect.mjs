import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const src = readFileSync(
  new URL("../../products/desktop/apps/web/src/web-oauth-flow.ts", import.meta.url),
  "utf8",
);
const tests = readFileSync(
  new URL("../../products/desktop/apps/web/src/web-oauth-flow.test.ts", import.meta.url),
  "utf8",
);

test("Flind Web OAuth refuses to follow refresh and authorization-code redirects", () => {
  assert.match(src, /redirect: "error"/);
  assert.match(src, /response\.status >= 300 && response\.status < 400/);
  assert.match(src, /prohibited redirect/);
  assert.match(tests, /\[301, 302, 303, 307, 308\]/);
  assert.match(tests, /mockRejectedValue/);
  assert.doesNotMatch(src, /posthog-code:oauth-callback/);
  assert.match(src, /flind-web:oauth-callback/);
});
