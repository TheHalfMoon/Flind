import { MarkdownRenderer } from "@flind/ui/features/editor/components/MarkdownRenderer";
import { MermaidDiagram } from "@flind/ui/primitives/MermaidDiagram";
import type { Meta, StoryObj } from "@storybook/react-vite";

const meta = {
  title: "Primitives/MermaidDiagram",
  component: MermaidDiagram,
  parameters: {
    layout: "padded",
  },
  decorators: [
    (Story) => (
      <div className="max-w-2xl">
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof MermaidDiagram>;

export default meta;
type Story = StoryObj<typeof meta>;

const FLOWCHART = `flowchart LR
  Capture[Capture API] --> Kafka
  Kafka --> Ingestion[Ingestion pipeline]
  Ingestion --> ClickHouse[(ClickHouse)]
  Ingestion --> Postgres[(Postgres)]
  ClickHouse --> App[Flind app]`;

const SEQUENCE = `sequenceDiagram
  participant App as Desktop app
  participant Agent
  participant Flind
  App->>Agent: Start task
  Agent->>Flind: Query insights
  Flind-->>Agent: Results
  Agent-->>App: Report with diagram`;

export const Flowchart: Story = {
  args: { code: FLOWCHART },
};

export const Sequence: Story = {
  args: { code: SEQUENCE },
};

export const InvalidSyntax: Story = {
  args: { code: "flowchart LR\n  A --> \n  --> B" },
};

/** A fence inside agent markdown swaps the code block for the diagram; other fences stay highlighted code. */
export const InsideMarkdown: Story = {
  render: () => (
    <MarkdownRenderer
      content={[
        "## Event flow",
        "",
        "Events land in ClickHouse after the ingestion pipeline:",
        "",
        "```mermaid",
        FLOWCHART,
        "```",
        "",
        "The capture call looks like this:",
        "",
        "```ts",
        'posthog.capture("signed_up", { plan: "free" })',
        "```",
      ].join("\n")}
    />
  ),
};
