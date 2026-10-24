import {
  ArrowSquareOut,
  CaretLeftIcon,
  CaretRightIcon,
} from "@phosphor-icons/react";
import { useHostTRPC, useHostTRPCClient } from "@flind/host-router/react";
import { Button, ButtonGroup, cn } from "@flind/quill";
import { BILLING_FLAG } from "@flind/shared";
import { ANALYTICS_EVENTS } from "@flind/shared/analytics-events";
import { isContentlessTask } from "@flind/shared/domain-types";
import { AnnouncementBanner } from "@flind/ui/features/announcements/AnnouncementBanner";
import { AnnouncementsHost } from "@flind/ui/features/announcements/AnnouncementsHost";
import { useServerArchiveSync } from "@flind/ui/features/archive/useServerArchiveSync";
import { useAuthStateValue } from "@flind/ui/features/auth/store";
import { UsageButton } from "@flind/ui/features/billing/UsageButton";
import { UsageLimitModal } from "@flind/ui/features/billing/UsageLimitModal";
import { useSpendGuardrails } from "@flind/ui/features/billing/useSpendGuardrails";
import { BrowserTabStrip } from "@flind/ui/features/browser-tabs/BrowserTabStrip";
import { BrowserTabsDndProvider } from "@flind/ui/features/browser-tabs/BrowserTabsDnd";
import { ChannelHotkeys } from "@flind/ui/features/canvas/components/ChannelHotkeys";
import { ChannelRouteSync } from "@flind/ui/features/canvas/components/ChannelRouteSync";
import { ChannelsSidebar } from "@flind/ui/features/canvas/components/ChannelsSidebar";
import { NavRail } from "@flind/ui/features/canvas/components/NavRail";
import { CanvasConnectorPermissionDialog } from "@flind/ui/features/canvas/freeform/CanvasConnectorPermissionDialog";
import { useCanvasDeepLink } from "@flind/ui/features/canvas/hooks/useCanvasDeepLink";
import { useChannelDeepLink } from "@flind/ui/features/canvas/hooks/useChannelDeepLink";
import { useChannelsLayout } from "@flind/ui/features/canvas/hooks/useChannelsLayout";
import { useChannelsWorld } from "@flind/ui/features/canvas/hooks/useChannelsWorld";
import { useRailSurface } from "@flind/ui/features/canvas/hooks/useRailSurface";
import { useShareLinkInterceptor } from "@flind/ui/features/canvas/hooks/useShareLinkInterceptor";
import { useShellOwnsHeader } from "@flind/ui/features/canvas/hooks/useShellOwnsHeader";
import { usePostHogWebFeedbackStore } from "@flind/ui/features/canvas/stores/posthogWebFeedbackStore";
import { CommandMenu } from "@flind/ui/features/command/CommandMenu";
import { GlobalFilePicker } from "@flind/ui/features/command/GlobalFilePicker";
import { KeyboardShortcutsSheet } from "@flind/ui/features/command/KeyboardShortcutsSheet";
import { ConnectivityBanner } from "@flind/ui/features/connectivity/ConnectivityBanner";
import { useNewTaskDeepLink } from "@flind/ui/features/deep-links/useNewTaskDeepLink";
import { useOpenTargetDeepLink } from "@flind/ui/features/deep-links/useOpenTargetDeepLink";
import { useTaskDeepLink } from "@flind/ui/features/deep-links/useTaskDeepLink";
import { useFeatureFlag } from "@flind/ui/features/feature-flags/useFeatureFlag";
import { useFeedbackStore } from "@flind/ui/features/feedback/feedbackStore";
import { useInboxDeepLink } from "@flind/ui/features/inbox/hooks/useInboxDeepLink";
import { useIntegrations } from "@flind/ui/features/integrations/useIntegrations";
import { useLoopDeepLink } from "@flind/ui/features/loops/hooks/useLoopDeepLink";
import { useScoutDeepLink } from "@flind/ui/features/scouts/hooks/useScoutDeepLink";
import { useSetupDiscovery } from "@flind/ui/features/setup/useSetupDiscovery";
import {
  UpdateBanner,
  useUpdateBannerVisible,
} from "@flind/ui/features/sidebar/components/UpdateBanner";
import { useNavRailMetrics } from "@flind/ui/features/sidebar/navRailSize";
import {
  beginSidebarPeek,
  cancelSidebarPeek,
  useSidebarPeekStore,
} from "@flind/ui/features/sidebar/sidebarPeekStore";
import { useSidebarStore } from "@flind/ui/features/sidebar/sidebarStore";
import { useSidebarData } from "@flind/ui/features/sidebar/useSidebarData";
import { useVisualTaskOrder } from "@flind/ui/features/sidebar/useVisualTaskOrder";
import { TileLayout } from "@flind/ui/features/tab-tiling/TileLayout";
import { useInTile } from "@flind/ui/features/tab-tiling/tileContext";
import { ExistingWorktreeDialog } from "@flind/ui/features/task-detail/components/ExistingWorktreeDialog";
import { RemoteBranchCheckoutDialog } from "@flind/ui/features/task-detail/components/RemoteBranchCheckoutDialog";
import { useTasks } from "@flind/ui/features/tasks/useTasks";
import { TourOverlay } from "@flind/ui/features/tour/components/TourOverlay";
import { WhatsNewModal } from "@flind/ui/features/updates/WhatsNewModal";
import { useWorkspaces } from "@flind/ui/features/workspace/useWorkspace";
import { AnimatedLogo } from "@flind/ui/primitives/AnimatedLogo";
import { useSettingsOverlay } from "@flind/ui/router/reportNavigation";
import { useAppView } from "@flind/ui/router/useAppView";
import { openTask, openTaskInput } from "@flind/ui/router/useOpenTask";
import { track } from "@flind/ui/shell/analytics";
import { ContentHeader } from "@flind/ui/shell/ContentHeader";
import { useCommandMenuStore } from "@flind/ui/shell/commandMenuStore";
import { GlobalEventHandlers } from "@flind/ui/shell/GlobalEventHandlers";
import { HedgehogMode } from "@flind/ui/shell/HedgehogMode";
import { logger } from "@flind/ui/shell/logger";
import { SpaceSwitcher } from "@flind/ui/shell/SpaceSwitcher";
import { useShortcutsSheetStore } from "@flind/ui/shell/shortcutsSheetStore";
import { useHostCapabilities } from "@flind/ui/shell/useHostCapabilities";
import { openUrlInBrowser } from "@flind/ui/utils/browser";
import { isMac, isWindows } from "@flind/ui/utils/platform";
import { getPostHogUrl } from "@flind/ui/utils/urls";
import { Box, Flex } from "@radix-ui/themes";
import { useQueryClient } from "@tanstack/react-query";
import {
  createRootRoute,
  Outlet,
  useCanGoBack,
  useRouter,
  useRouterState,
} from "@tanstack/react-router";
import { SidebarClose, SidebarOpen } from "lucide-react";
import { useEffect, useRef, useState } from "react";

// The router devtools render their genuine floating overlay, mounted by the
// app's dev toolbar with the floating logo hidden so the toolbar owns the
// trigger — see RouterDevtools.

const log = logger.scope("root-route");

// On Windows the frameless window overlays the min/max/close controls on the
// top-right of the title bar (see window.ts titleBarOverlay). Reserve that strip
// so the tab strip / PostHog Web button never render under the native controls.
const WINDOWS_TITLEBAR_INSET = 140;

export const Route = createRootRoute({
  component: RootRoute,
});

function RootRoute() {
  return useInTile() ? <Outlet /> : <RootLayout />;
}

function RootLayout() {
  const view = useAppView();
  const router = useRouter();
  const canGoBack = useCanGoBack();
  // Cloud-only hosts (web) run in a real browser tab that already provides
  // native back/forward chrome, so the in-app history buttons are redundant.
  const { localWorkspaces } = useHostCapabilities();
  // Forward availability isn't exposed by the router (and history.length counts
  // pre-app entries, so it can't be compared to __TSR_index). Track the newest
  // index we've reached: only a PUSH wipes the forward stack, so it resets the
  // newest to the current index. REPLACE mutates the current entry in place
  // (index unchanged, forward entries intact) and BACK/GO just move within the
  // existing stack, so both keep the max. Forward is live while below it.
  const historyIndex = useRouterState({
    select: (s) => s.location.state.__TSR_index,
  });
  const [newestIndex, setNewestIndex] = useState(historyIndex);
  useEffect(() => {
    return router.history.subscribe(({ location, action }) => {
      const idx = location.state.__TSR_index;
      setNewestIndex((prev) =>
        action.type === "PUSH" ? idx : Math.max(prev, idx),
      );
    });
  }, [router]);
  const canGoForward = historyIndex < newestIndex;

  const currentProjectId = useAuthStateValue((s) => s.currentProjectId);

  // The user's current project on the correct cloud (region comes from
  // cloudRegion via getPostHogUrl), falling back to the account root. `null`
  // when the region is unknown — the "PostHog Web" button is disabled then, so
  // a click can never silently no-op.
  const posthogWebUrl = getPostHogUrl(
    currentProjectId ? `/project/${currentProjectId}` : "/",
  );

  const posthogWebFeedbackSeen = usePostHogWebFeedbackStore((s) => s.hasSeen);
  const posthogWebFeedbackHydrated = usePostHogWebFeedbackStore(
    (s) => s.hasHydrated,
  );
  const markPostHogWebFeedbackSeen = usePostHogWebFeedbackStore(
    (s) => s.markSeen,
  );
  const openFeedback = useFeedbackStore((s) => s.open);

  const handleOpenPostHogWeb = () => {
    track(ANALYTICS_EVENTS.POSTHOG_WEB_OPENED);
    if (posthogWebFeedbackHydrated && posthogWebFeedbackSeen && posthogWebUrl) {
      void openUrlInBrowser(posthogWebUrl);
      return;
    }
    if (posthogWebUrl) {
      openFeedback("posthog-web", () => {
        markPostHogWebFeedbackSeen();
        void openUrlInBrowser(posthogWebUrl);
      });
    }
  };
  const {
    isOpen: commandMenuOpen,
    setOpen: setCommandMenuOpen,
    toggle: toggleCommandMenu,
  } = useCommandMenuStore();
  const {
    isOpen: shortcutsSheetOpen,
    close: closeShortcutsSheet,
    toggle: toggleShortcutsSheet,
  } = useShortcutsSheetStore();
  const { data: tasks } = useTasks();
  const { data: workspaces, isFetched: workspacesFetched } = useWorkspaces();
  const trpc = useHostTRPC();
  const hostClient = useHostTRPCClient();
  const queryClient = useQueryClient();
  const reconcilingTaskIds = useRef<Set<string>>(new Set());
  const billingEnabled = useFeatureFlag(BILLING_FLAG);
  useSpendGuardrails();
  // "PostHog Web" is a channels-world affordance — show it only while the user
  // is actually seeing channels.
  const channelsWorld = useChannelsWorld();
  // The new channels layout has exactly one gate: its feature flag (no
  // sidebar toggle). When on it subsumes the channels alpha entirely.
  const channelsLayout = useChannelsLayout();
  const { width: navRailWidth } = useNavRailMetrics();
  const { hasSidebar } = useRailSurface();
  // When the sidebar is collapsed (Cmd+B) the title bar's left block shrinks to
  // fit its own controls so the tab strip flushes left with the content pane.
  const sidebarOpen = useSidebarStore((s) => s.open);
  // On screen, not merely un-collapsed: a destination with no list takes the
  // column away whatever the open flag says.
  const sidebarDocked = sidebarOpen && hasSidebar;
  // The corner belongs to whichever pane starts the framed inset.
  const framesOwnCorner = channelsLayout ? !sidebarDocked : sidebarDocked;

  const toggleSidebar = useSidebarStore((s) => s.toggle);
  const sidebarPeek = useSidebarPeekStore((s) => s.peek);
  const updateBannerVisible = useUpdateBannerVisible();
  const showTitleBarUpdate =
    updateBannerVisible && !sidebarDocked && !sidebarPeek;
  // Toggling makes any hover-peek redundant (opening replaces the overlay;
  // closing must not leave it lingering under the pointer).
  const handleToggleSidebar = (): void => {
    cancelSidebarPeek();
    toggleSidebar();
  };

  const sidebarData = useSidebarData({ activeView: view });
  const visualTaskOrder = useVisualTaskOrder(sidebarData);
  const activeTaskId =
    view.type === "task-detail" && view.taskId ? view.taskId : null;

  useIntegrations();
  useTaskDeepLink();
  useOpenTargetDeepLink();
  useInboxDeepLink();
  useScoutDeepLink();
  useCanvasDeepLink();
  useChannelDeepLink();
  useLoopDeepLink();
  useShareLinkInterceptor();
  useSetupDiscovery();
  useNewTaskDeepLink();
  useServerArchiveSync();

  // hydrateTask is no longer needed — the URL is the source of truth and the
  // task cache populates the route automatically.

  useEffect(() => {
    if (!tasks || !workspaces || !workspacesFetched) return;
    const missing = tasks.filter(
      (t) =>
        t.latest_run?.environment === "cloud" &&
        !workspaces[t.id] &&
        !reconcilingTaskIds.current.has(t.id) &&
        !isContentlessTask(t),
    );
    if (missing.length === 0) return;
    const missingIds = missing.map((t) => t.id);
    for (const id of missingIds) reconcilingTaskIds.current.add(id);
    // Single batched IPC instead of one mutation per task — with many cloud
    // tasks the per-task pattern saturates the main thread at boot.
    hostClient.workspace.reconcileCloudWorkspaces
      .mutate({ taskIds: missingIds })
      .then((result) => {
        for (const id of missingIds) reconcilingTaskIds.current.delete(id);
        if (result.created.length > 0) {
          void queryClient.invalidateQueries({
            queryKey: trpc.workspace.getAll.queryKey(),
          });
        }
      })
      .catch((err) => {
        for (const id of missingIds) reconcilingTaskIds.current.delete(id);
        log.warn("Failed to reconcile cloud workspaces", err);
      });
  }, [tasks, workspaces, workspacesFetched, queryClient, hostClient, trpc]);

  // Settings is a full-page route — drop the app chrome (header/sidebar/
  // space-switcher) so the panel occupies the full window. A report opened
  // from settings hosts the same portal, so it counts as settings here too.
  const isSettingsRoute = useSettingsOverlay();

  // ShellLayout draws the in-pane header under `_shell`, so the shared
  // ContentHeader is mounted only where that layout isn't.
  const shellOwnsHeader = useShellOwnsHeader();

  return (
    // DnD scope for the tab strip's drag-to-reorder (pill sortables live in
    // the title bar; the provider must sit above them).
    <BrowserTabsDndProvider>
      {/* Settings renders over this tree through a portal. Going inert keeps
          focus and clicks out of the covered chrome without unmounting it. */}
      <Flex
        direction="column"
        height="100%"
        className="bg-chrome"
        inert={isSettingsRoute}
      >
        {/* Full-width title bar: a window-drag region carrying the PostHog
            mark. The left section sizes to its controls so the tab strip sits
            beside the history buttons; its padding clears the macOS stoplights
            via env(titlebar-area-x), the system-reported right edge of the
            traffic-light strip (see titleBarOverlay in window.ts). */}
        <Flex
          align="center"
          className="drag h-10 shrink-0"
          style={{
            paddingRight: isWindows ? WINDOWS_TITLEBAR_INSET : undefined,
          }}
        >
          <Flex
            id="title-bar-left"
            align="center"
            justify="start"
            gap="3"
            className="shrink-0 pr-2"
            style={{
              // Traffic-light size varies by macOS version, so a fixed inset
              // over- or under-shoots; the env var fallback covers hosts
              // without Window Controls Overlay.
              paddingLeft: isMac ? "env(titlebar-area-x, 78px)" : "78px",
            }}
          >
            <Flex align="center" gap="2" className="no-drag">
              <AnimatedLogo size={26} animate="hover" />
              <Button
                size="icon-sm"
                aria-label="Toggle sidebar"
                onClick={handleToggleSidebar}
                onMouseEnter={() => {
                  if (!sidebarOpen && hasSidebar) beginSidebarPeek();
                }}
              >
                {sidebarOpen ? (
                  <SidebarClose size={10} className="text-muted-foreground" />
                ) : (
                  <SidebarOpen size={10} className="text-muted-foreground" />
                )}
              </Button>
            </Flex>
            {localWorkspaces && (
              <ButtonGroup className="no-drag">
                <Button
                  variant="outline"
                  size="icon-sm"
                  aria-label="Back"
                  disabled={!canGoBack}
                  onClick={() => router.history.back()}
                >
                  <CaretLeftIcon size={14} />
                </Button>
                <Button
                  variant="outline"
                  size="icon-sm"
                  aria-label="Forward"
                  disabled={!canGoForward}
                  onClick={() => router.history.forward()}
                >
                  <CaretRightIcon size={14} />
                </Button>
              </ButtonGroup>
            )}
          </Flex>
          {/* The strip owns the title bar's middle in both layouts. Search
              moved to the rail to make room for it (see NavRail). The strip is
              also the only global owner of Cmd+W, so the fallback has to hold
              that key wherever the strip isn't mounted. */}
          <BrowserTabStrip />
          {showTitleBarUpdate && (
            <div className="no-drag ml-auto flex items-center pr-2">
              <UpdateBanner variant="compact" />
            </div>
          )}
          {/* Gated so an empty right-side group can't claim a no-drag rect
              in the title bar for nothing — every pixel without controls
              should drag the window. */}
          {(billingEnabled || channelsWorld) && (
            <Flex align="center" gap="2" className="no-drag ml-auto pr-3">
              <UsageButton />
              {channelsWorld && (
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!posthogWebUrl}
                  onClick={handleOpenPostHogWeb}
                >
                  <ArrowSquareOut size={14} />
                  PostHog Web
                </Button>
              )}
            </Flex>
          )}
        </Flex>
        {/* Settings draws its own copies over this tree — see the settings
            route. One instance of each at a time, so an announcement is not
            reported as seen twice. */}
        {!isSettingsRoute && <ConnectivityBanner />}
        <Flex flexGrow="1" overflow="hidden" className="relative">
          {/* Scrim under the peeked nav: dims the content while the overlay is
              out. Purely visual (pointer-transparent) and paired with the
              panel's slide — same 200ms ease-out — so they read as one unit. */}
          {!sidebarOpen && (
            <Box
              aria-hidden
              style={{ left: channelsLayout ? navRailWidth : 0 }}
              // The radix preset replaces Tailwind's palette, so plain
              // `bg-black/*` doesn't exist — use the radix black-alpha scale
              // (--black-a2 = 10%, --black-a5 = 30%).
              className={`pointer-events-none absolute inset-0 z-40 bg-blackA-2 transition-opacity duration-200 ease-out motion-reduce:transition-none dark:bg-blackA-5 ${
                sidebarPeek ? "opacity-100" : "opacity-0"
              }`}
            />
          )}
          {/* Outside the sidebar on purpose: collapsing the sidebar (Cmd+B)
              must not take the destinations with it. */}
          {channelsLayout && <NavRail />}
          {hasSidebar && <ChannelsSidebar />}
          {/* Content sits in a bordered, rounded card inset from the window
              edges — the framed pane from the design. The rounded corner
              belongs to whichever pane starts the inset: the sidebar when it
              is docked, this pane when it isn't and the rail holds the edge.
              Without a rail there is nothing to inset from until the sidebar
              opens, which is the corner this pane kept before. */}
          <Box flexGrow="1" className="overflow-hidden">
            <Box
              className={cn(
                "h-full overflow-hidden border-border border-t bg-background",
                // A docked sidebar already draws this edge; two owners stack
                // two 1px lines into one seam.
                !sidebarDocked && "border-l",
                framesOwnCorner && "rounded-tl-sm",
              )}
            >
              <Flex direction="column" height="100%">
                {/* Inside the framed pane, not the app column: announcements
                    overlay the content, never the sidebar. */}
                {!isSettingsRoute && <AnnouncementBanner />}
                {/* The shell renders its own header (ShellLayout);
                      everywhere else the shared header carries the view title
                      and, on a task, its action row. */}
                {!shellOwnsHeader && <ContentHeader />}
                <Box flexGrow="1" overflow="hidden">
                  <TileLayout>
                    <Outlet />
                  </TileLayout>
                </Box>
              </Flex>
            </Box>
          </Box>
        </Flex>
        <CommandMenu open={commandMenuOpen} onOpenChange={setCommandMenuOpen} />
        <GlobalFilePicker />
        <KeyboardShortcutsSheet
          open={shortcutsSheetOpen}
          onOpenChange={(open) => (open ? null : closeShortcutsSheet())}
        />
        <GlobalEventHandlers
          allTasks={tasks ?? []}
          onToggleCommandMenu={toggleCommandMenu}
          onToggleShortcutsSheet={toggleShortcutsSheet}
          visualTaskOrder={visualTaskOrder}
        />
        {/* Renders nothing — owns ⌘1-9 under the channels layout. Mounted here
            rather than in the switcher, which only exists once a channel is
            already scoped. */}
        {!isSettingsRoute && <ChannelHotkeys />}
        {/* Renders nothing — owns which space is scoped. The sidebar used to,
            but the rail can take that column away and the scoping still has to
            happen. */}
        <ChannelRouteSync />
        {/* Renders nothing — wires the ⌥↑/⌥↓ task-cycling shortcuts. */}
        <SpaceSwitcher
          tasks={visualTaskOrder}
          activeTaskId={activeTaskId}
          allTasks={tasks ?? []}
          isOnNewTask={view.type === "task-input"}
          onNavigateToTask={openTask}
          onNewTask={openTaskInput}
        />
        <TourOverlay />
        {billingEnabled && <UsageLimitModal />}
        <AnnouncementsHost />
        <WhatsNewModal />
        <RemoteBranchCheckoutDialog />
        <ExistingWorktreeDialog />
        <CanvasConnectorPermissionDialog />
        <HedgehogMode />
      </Flex>
    </BrowserTabsDndProvider>
  );
}
