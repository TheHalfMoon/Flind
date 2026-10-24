import type { TaskSearchResult } from "@flind/shared/domain-types";
import { Theme } from "@radix-ui/themes";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

vi.mock("@flind/ui/features/browser-tabs/useOpenBrowserTab", () => ({
  useOpenBrowserTab: () => vi.fn(),
}));
vi.mock("@flind/ui/shell/analytics", () => ({ track: vi.fn() }));
vi.mock("@flind/ui/features/auth/authClient", () => ({
  useOptionalAuthenticatedClient: () => null,
}));
vi.mock("@flind/ui/features/auth/useCurrentUser", () => ({
  useCurrentUser: () => ({ data: { uuid: "user-1" } }),
}));
vi.mock("@flind/di/container", () => ({
  resolveService: () => ({}),
  resolveServiceOptional: () => null,
}));
vi.mock("@flind/ui/features/feature-flags/useFeatureFlag", () => ({
  useFeatureFlag: () => false,
}));
vi.mock("@flind/ui/features/archive/useArchivedTaskIds", () => ({
  useArchivedTaskIds: () => new Set(),
}));
vi.mock("@flind/ui/features/archive/useTaskArchive", () => ({
  useTaskArchive: () => ({
    requestArchive: vi.fn(),
    isArchiving: false,
    dialog: null,
  }),
}));
vi.mock("@flind/ui/features/workspace/useWorkspace", () => ({
  useWorkspaces: () => ({ data: [], isFetched: false }),
}));
vi.mock("@flind/ui/features/canvas/hooks/useChannels", () => ({
  useChannels: () => ({ channels: [], isLoading: false }),
}));
vi.mock("@flind/ui/features/canvas/hooks/useChannelsLayout", () => ({
  useChannelsLayout: () => false,
}));
vi.mock("@flind/ui/features/canvas/hooks/useCanvasQueryResults", () => ({
  useCanvasQueryResults: () => ({
    canvases: [],
    isLoading: false,
  }),
}));
vi.mock("@flind/ui/features/canvas/hooks/useTaskFeedResults", () => ({
  useTaskFeedResults: () => ({
    tasks: [],
    isComplete: true,
    isLoading: false,
    issues: [],
  }),
  useFeedQueryPlan: () => ({ plan: undefined, isLoading: false }),
}));
vi.mock("@flind/ui/features/folders/useFolders", () => ({
  useFolders: () => ({ folders: [] }),
}));
vi.mock("@flind/ui/router/useAppView", () => ({
  useAppView: () => ({ type: "home" }),
}));
vi.mock("@flind/ui/features/canvas/hooks/useOrgMembers", () => ({
  useOrgMembers: () => ({
    members: [],
    isLoading: false,
    isError: false,
    isComplete: true,
  }),
}));
vi.mock("@flind/ui/features/sidebar/useTaskPrStatus", () => ({
  useTaskPrStatus: () => ({ prState: null, hasDiff: false, prUrl: null }),
}));
vi.mock("@flind/ui/features/canvas/hooks/useTaskChannelMap", () => ({
  useTaskChannelMap: () => new Map(),
}));
vi.mock("@flind/ui/features/command/useFileSearchContext", () => ({
  useFileSearchContext: () => ({ repoPath: null }),
}));

vi.mock("@flind/ui/features/tasks/useTasks", () => ({
  useTasks: () => ({
    data: [{ id: "task-a", title: "Run analytics queries", channel: null }],
  }),
}));

const searchResults: TaskSearchResult[] = [
  {
    id: "doc-task",
    kind: "task",
    title: "Run analytics queries",
    subtitle: "",
    task_id: "task-a",
    task_run_id: null,
    channel_id: null,
    updated_at: "2026-09-01T10:00:00Z",
    metadata: {},
  },
  {
    id: "doc-file",
    kind: "artifact",
    title: "run-log.jsonl",
    subtitle: "Nightly import check",
    task_id: "task-b",
    task_run_id: null,
    channel_id: null,
    updated_at: "2026-09-01T09:00:00Z",
    metadata: {},
  },
];
vi.mock("@flind/ui/features/command/useTaskSearch", () => ({
  useTaskSearch: (query: string) => ({
    data: query ? searchResults : [],
  }),
}));

import { CommandMenu } from "./CommandMenu";

describe("CommandMenu global search", () => {
  it("lists a matching task above the files, without repeating it below", async () => {
    const user = userEvent.setup();
    render(
      <Theme>
        <CommandMenu open onOpenChange={() => {}} />
      </Theme>,
    );

    await user.type(
      screen.getByPlaceholderText(/Search commands, channels, and tasks/),
      "run",
    );

    await screen.findByText("run-log.jsonl");
    const rows = Array.from(document.querySelectorAll("[role='option']")).map(
      (row) => row.textContent,
    );
    expect(rows[0]).toContain("Run analytics queries");
    expect(rows[1]).toContain("run-log.jsonl");
    expect(screen.queryByText("Tasks")).toBeNull();
  });
});
