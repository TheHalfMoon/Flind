import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";
import { posthogSrcAliases } from "./vite.aliases";

const directory = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  root: directory,
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
  resolve: {
    alias: posthogSrcAliases,
  },
});
