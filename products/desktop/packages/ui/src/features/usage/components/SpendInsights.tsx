import { Sparkle } from "@phosphor-icons/react";
import { windowDays } from "@flind/core/billing/spendAnalysisFormat";
import { buildAnalysisPrompt } from "@flind/core/billing/spendAnalysisPrompt";
import type { SpendAnalysisResponse } from "@flind/core/billing/spendAnalysisTypes";
import { deriveSpendSuggestions } from "@flind/core/billing/spendSuggestions";
import { ANALYTICS_EVENTS } from "@flind/shared/analytics-events";
import { openTaskInput } from "@flind/ui/router/useOpenTask";
import { track } from "@flind/ui/shell/analytics";
import { Button, Flex, Separator, Text } from "@radix-ui/themes";
import { UsageCard } from "./UsageCard";

const DOCS_URL = "https://posthog.com/docs/ai-observability";

export function SpendInsights({ data }: { data: SpendAnalysisResponse }) {
  const suggestions = deriveSpendSuggestions(data);

  const handleAnalyseClick = (): void => {
    track(ANALYTICS_EVENTS.SPEND_ANALYSIS_TASK_OPENED, {
      total_cost_usd: data.summary.total_cost_usd,
      scoped_cost_usd: data.summary.scoped_cost_usd,
      scoped_event_count: data.summary.scoped_event_count,
      window_days: windowDays(data.summary.date_from, data.summary.date_to),
      tool_row_count: Math.min(data.by_tool.items.length, 10),
      model_row_count: data.by_model.items.length,
    });
    openTaskInput({
      initialPrompt: buildAnalysisPrompt(data),
    });
  };

  return (
    <UsageCard
      icon={<Sparkle size={14} className="text-(--accent-9)" />}
      title="Where to look"
    >
      <Flex direction="column" gap="2">
        {suggestions.map((s) => (
          <Text key={s} className="text-(--gray-11) text-[13px]">
            {s}
          </Text>
        ))}
      </Flex>
      <Separator size="4" />
      <Flex direction="column" gap="3">
        <Text className="text-(--gray-11) text-[13px]">
          Use{" "}
          <a
            href={DOCS_URL}
            target="_blank"
            rel="noreferrer"
            className="text-(--accent-11) underline"
          >
            Flind AI observability
          </a>{" "}
          in your own project for the full slice-and-dice experience.
        </Text>
        <Button
          size="1"
          variant="soft"
          onClick={handleAnalyseClick}
          className="self-start"
        >
          <Sparkle size={12} />
          Open a task to analyse this with an agent
        </Button>
      </Flex>
    </UsageCard>
  );
}
