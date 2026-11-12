import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { flindAnalyticsOrigin } from "../../products/desktop/packages/shared/src/analyticsOrigin.ts";

const read = (path) =>
  readFileSync(new URL("../../" + path, import.meta.url), "utf8");

test("desktop analytics has no inherited provider collector and requires HTTPS", () => {
  for (const value of [
    undefined,
    "",
    "http://telemetry.flind.example",
    "https://us.i.posthog.com",
    "https://internal-c.posthog.com",
    "https://eu.posthog.com",
    "https://posthog.dev",
    "https://user:secret@telemetry.flind.example",
    "https://telemetry.flind.example/path",
    "https://telemetry.flind.example?token=example",
    "bad URL",
  ]) {
    assert.equal(flindAnalyticsOrigin(value), null, String(value));
  }
  assert.equal(
    flindAnalyticsOrigin("https://telemetry.flind.example/"),
    "https://telemetry.flind.example",
  );
});

test("desktop UI, Node SDK and OTLP logs cannot read inherited telemetry credentials", () => {
  const clients = [
    "products/desktop/packages/ui/src/shell/posthogAnalyticsImpl.ts",
    "products/desktop/apps/code/src/main/platform-adapters/posthog-analytics.ts",
    "products/desktop/apps/code/src/main/utils/otel-log-transport.ts",
  ];
  for (const file of clients) {
    const src = read(file);
    assert.match(src, /VITE_FLIND_ANALYTICS_KEY/);
    assert.match(src, /VITE_FLIND_ANALYTICS_HOST/);
    assert.match(src, /flindAnalyticsOrigin/);
    assert.doesNotMatch(src, /VITE_POSTHOG_API_(?:KEY|HOST)/);
    assert.doesNotMatch(src, /internal-c\.posthog\.com|us\.i\.posthog\.com/);
  }
  for (const file of [
    "products/desktop/apps/code/electron.vite.config.ts",
    "products/desktop/apps/code/vite.main.config.mts",
  ]) {
    const src = read(file);
    assert.match(src, /process\.env\.VITE_FLIND_ANALYTICS_KEY/);
    assert.match(src, /process\.env\.VITE_FLIND_ANALYTICS_HOST/);
    assert.doesNotMatch(src, /process\.env\.VITE_POSTHOG_API_(?:KEY|HOST)/);
  }
});

test("an unconfigured telemetry key or collector disables all three desktop paths", () => {
  const renderer = read("products/desktop/packages/ui/src/shell/posthogAnalyticsImpl.ts");
  const main = read("products/desktop/apps/code/src/main/platform-adapters/posthog-analytics.ts");
  const otlp = read("products/desktop/apps/code/src/main/utils/otel-log-transport.ts");
  assert.match(renderer, /if \(!apiKey \|\| !apiHost \|\| !uiHost\)/);
  assert.match(main, /if \(!apiKey \|\| !apiHost\)/);
  assert.match(otlp, /if \(!apiKey \|\| !apiHost\)/);
});
