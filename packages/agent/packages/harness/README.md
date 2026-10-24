# @flind/harness

PostHog's [Pi](https://pi.dev) distribution.

It adds the PostHog LLM provider and the extensions in `src/extensions/` while keeping Pi's native runtime, sessions, tools, and RPC protocol.

## CLI

```bash
hog
hog /login
hog -p "Fix the tests" --model posthog/claude-opus-4-8
```

`harness` is an alias for `hog`.

## Runtime

```ts
import { createHarnessRuntime } from "@flind/harness";

const runtime = await createHarnessRuntime({ cwd: "/workspace" });

await runtime.session.prompt("Fix the tests");
```

`createHarnessRuntime()` returns Pi's native `AgentSessionRuntime`.

## RPC

```ts
import { createHarnessRuntime, runRpcMode } from "@flind/harness";

const runtime = await createHarnessRuntime({ cwd: "/workspace" });
await runRpcMode(runtime);
```

RPC is Pi's JSONL protocol over stdin/stdout. Harness does not define another protocol.

## Authentication

Run `hog /login`, or pass a PostHog personal API key:

```ts
const runtime = await createHarnessRuntime({ apiKey: "pha_…" });
```

Set `POSTHOG_REGION` to `us`, `eu`, or `dev` when needed.

## Public API

| Import | Purpose |
| --- | --- |
| `@flind/harness` | Runtime creation and RPC mode |
| `@flind/harness/runtime` | Runtime creation only |
| `@flind/harness/extensions` | Harness extension registry |
| `@flind/harness/extensions/context-wiki` | Context-wiki prompt and environment helpers |
| `@flind/harness/extensions/enrichment` | File enrichment behavior |
| `@flind/harness/extensions/task-system-prompt` | Task prompt builders and Pi task-prompt extension |
| `@flind/harness/extensions/posthog-mcp-policy` | PostHog MCP permission policy and product-id classification |
| `@flind/harness/extensions/local-tools` | Injected local tools (signed git, artifacts, peer messaging) and their PostHog task/run API client |
| `@flind/harness/extensions/rtk` | RTK command-compression: Pi's native rewrite, the pure matching rules Claude's hook uses, and the Codex guidance text |
| `@flind/harness/extensions/benjamin` | Vendored Benjamin-Plus and Simplified Technical English (ASD-STE100) system-prompt instructions, gated by `POSTHOG_BENJAMIN` |
| `@flind/harness/extensions/agent-instructions` | Base appended system-prompt content (branch naming, PR links, plan mode, shell efficiency, spoken narration, …) |
| `@flind/harness/extensions/skills-store` | PostHog skills-store pointer-file rendering and install/remove across Claude Code, Codex, and Pi skill roots |

Individual extensions are also exported under `@flind/harness/extensions/*`.
