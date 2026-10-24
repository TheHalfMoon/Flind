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
  useFeatureFlag: () => true,
}));
vi.mock("@flind/ui/features/tasks/useTasks", () => ({
  useTasks: () => ({ data: [] }),
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
  useWorkspaces: () => ({ data: [], isFetched: true }),
}));
vi.mock("@flind/ui/features/canvas/hooks/useChannels", () => ({
  useChannels: () => ({ channels: [], isLoading: false }),
}));
vi.mock("@flind/ui/features/canvas/hooks/useOrgMembers", () => ({
  useOrgMembers: () => ({
    members: [],
    isLoading: false,
    isError: false,
    isComplete: true,
  }),
}));
vi.mock("@flind/ui/features/canvas/hooks/useChannelsLayout", () => ({
  useChannelsLayout: () => true,
}));
vi.mock("@flind/ui/features/canvas/hooks/useTaskChannelMap", () => ({
  useTaskChannelMap: () => new Map(),
}));
vi.mock("@flind/ui/features/command/useFileSearchContext", () => ({
  useFileSearchContext: () => ({ repoPath: null }),
}));
vi.mock("@flind/ui/features/command/useTaskSearch", () => ({
  useTaskSearch: () => ({ data: [] }),
}));
vi.mock("@flind/ui/features/folders/useFolders", () => ({
  useFolders: () => ({ folders: [] }),
}));
vi.mock("@flind/ui/router/useAppView", () => ({
  useAppView: () => ({ type: "home" }),
}));
vi.mock("@flind/ui/features/sidebar/useTaskPrStatus", () => ({
  useTaskPrStatus: () => ({ prState: null, hasDiff: false, prUrl: null }),
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
vi.mock("@flind/ui/features/canvas/components/CreateChannelModal", () => ({
  CreateChannelModal: ({ open }: { open: boolean }) =>
    open ? <div>create space modal</div> : null,
}));

import { CommandMenu } from "./CommandMenu";

describe("CommandMenu space creation", () => {
  it("opens the create modal from the New space command", async () => {
    const user = userEvent.setup();
    render(<CommandMenu open onOpenChange={vi.fn()} />);

    expect(screen.queryByText("create space modal")).not.toBeInTheDocument();
    await user.click(await screen.findByText("New space"));
    expect(await screen.findByText("create space modal")).toBeInTheDocument();
  });
});
