import { getAuthIdentity } from "@flind/core/auth/authIdentity";
import { ToastProvider } from "@flind/quill";
import { isNotAuthenticatedError } from "@flind/shared";
import { useOptionalAuthenticatedClient } from "@flind/ui/features/auth/authClient";
import { useAuthStateValue } from "@flind/ui/features/auth/authQueries";
import { AuthScreen } from "@flind/ui/features/auth/components/AuthScreen";
import { DesktopAccessScreen } from "@flind/ui/features/auth/components/DesktopAccessScreen";
import { ScopeReauthPrompt } from "@flind/ui/features/auth/components/ScopeReauthPrompt";
import {
  useLogoutMutation,
  useRetryDesktopAccessMutation,
  useSelectProjectMutation,
  useSwitchOrgMutation,
} from "@flind/ui/features/auth/useAuthMutations";
import { useAuthSession } from "@flind/ui/features/auth/useAuthSession";
import { useIsOrgAdmin } from "@flind/ui/features/auth/useOrgRole";
import { CanvasGenerationToaster } from "@flind/ui/features/canvas/freeform/useCanvasGenerationToasts";
import { useChannelsLayout } from "@flind/ui/features/canvas/hooks/useChannelsLayout";
import { showChannelList } from "@flind/ui/features/canvas/stores/channelPaneStore";
import { useSpaceTreeStore } from "@flind/ui/features/canvas/stores/spaceTreeStore";
import { ConnectivityBanner } from "@flind/ui/features/connectivity/ConnectivityBanner";
import { ConsentScreen } from "@flind/ui/features/consent/ConsentScreen";
import { useConsentAnalytics } from "@flind/ui/features/consent/consentAnalytics";
import { useOrgConsent } from "@flind/ui/features/consent/useOrgConsent";
import { FeedbackHost } from "@flind/ui/features/feedback/FeedbackHost";
import { AddDirectoryDialog } from "@flind/ui/features/folder-picker/AddDirectoryDialog";
import { NewLoopDialog } from "@flind/ui/features/loops/components/NewLoopDialog";
import { ErrorDetailsDialog } from "@flind/ui/features/notifications/ErrorDetailsDialog";
import { OnboardingFlow } from "@flind/ui/features/onboarding/components/OnboardingFlow";
import { useOnboardingStore } from "@flind/ui/features/onboarding/onboardingStore";
import { SettingsDialog } from "@flind/ui/features/settings/SettingsDialog";
import { UpdateBanner } from "@flind/ui/features/sidebar/components/UpdateBanner";
import { PendingPromptRecovery } from "@flind/ui/features/task-detail/components/PendingPromptRecovery";
import { UpdateAvailableModal } from "@flind/ui/features/updates/UpdateAvailableModal";
import { router } from "@flind/ui/router/router";
import { AppLoadingScreen } from "@flind/ui/shell/AppLoadingScreen";
import {
  isBackgroundAccessRecheck,
  nextLastAllowedProjectId,
} from "@flind/ui/shell/desktopAccessGate";
import { ErrorBoundary } from "@flind/ui/shell/ErrorBoundary";
import { flindExternalUrl } from "@flind/ui/shell/flindExternalLinks";
import { ensureSession } from "@flind/ui/shell/firstRun";
import { logger } from "@flind/ui/shell/logger";
import { openExternalUrl } from "@flind/ui/shell/openExternal";
import {
  rememberStartupLocation,
  resolveStartupLocation,
} from "@flind/ui/shell/startupLocation";
import { useAppLoadingGateTelemetry } from "@flind/ui/shell/useAppLoadingGateTelemetry";
import { useAppVisibilityWatchdog } from "@flind/ui/shell/useAppVisibilityWatchdog";
import { RouterProvider } from "@tanstack/react-router";
import { AnimatePresence, motion } from "framer-motion";
import { type ReactNode, useEffect, useRef, useState } from "react";

interface AppProps {
  /** Host-provided dev diagnostics toolbar, docked below the app content. */
  devToolbar?: ReactNode;
}

const log = logger.scope("app");

function App({ devToolbar }: AppProps) {
  const { isBootstrapped } = useAuthSession();
  const authState = useAuthStateValue((state) => state);
  const hasCompletedOnboarding = useOnboardingStore(
    (state) => state.hasCompletedOnboarding,
  );
  const isAuthenticated = authState.status === "authenticated";
  const desktopAccess = authState.desktopAccess;
  const selectProjectMutation = useSelectProjectMutation();
  const switchOrgMutation = useSwitchOrgMutation();
  const retryDesktopAccessMutation = useRetryDesktopAccessMutation();
  const logoutMutation = useLogoutMutation();
  const desktopAccessIsCurrent =
    desktopAccess.projectId === authState.currentProjectId;
  const hasDesktopAccess =
    desktopAccessIsCurrent && desktopAccess.status === "allowed";
  // Once the app has shown for a project, a background access recheck for
  // that same project must not unmount it into the loading screen (see
  // isBackgroundAccessRecheck). The ref updates in an effect, so when a
  // "checking" flip renders it still holds the project from the last settled
  // render.
  const lastAllowedProjectRef = useRef<number | null>(null);
  useEffect(() => {
    lastAllowedProjectRef.current = nextLastAllowedProjectId(
      lastAllowedProjectRef.current,
      {
        isAuthenticated,
        currentProjectId: authState.currentProjectId,
        accessIsCurrent: desktopAccessIsCurrent,
        accessStatus: desktopAccess.status,
      },
    );
  }, [
    isAuthenticated,
    authState.currentProjectId,
    desktopAccessIsCurrent,
    desktopAccess.status,
  ]);
  const isRevalidatingAccess =
    desktopAccessIsCurrent &&
    isBackgroundAccessRecheck(
      lastAllowedProjectRef.current,
      authState.currentProjectId,
      desktopAccess.status,
    );
  const settledDesktopAccess = hasDesktopAccess || isRevalidatingAccess;
  const switchError =
    selectProjectMutation.isError || switchOrgMutation.isError
      ? "Couldn't switch your selection. Try again."
      : null;
  // Analytics init + dev inbox console moved to host CONTRIBUTIONs
  // (AnalyticsBootContribution / InboxDemoDevContribution), started by
  // boot at boot.

  // Workspace, focus, and agent event listeners moved to their feature
  // CONTRIBUTIONs (WorkspaceEventsContribution / FocusEventsContribution
  // / AgentEventsContribution), started by boot at boot.

  const isBlockedByAccessPolicy =
    isAuthenticated &&
    desktopAccessIsCurrent &&
    ["blocked", "error"].includes(desktopAccess.status);
  const authenticatedClient = useOptionalAuthenticatedClient();
  const consent = useOrgConsent(isAuthenticated && settledDesktopAccess);
  const needsConsent =
    isAuthenticated &&
    hasCompletedOnboarding &&
    settledDesktopAccess &&
    consent.status === "resolved" &&
    !consent.satisfied;
  const isCheckingAccess =
    isAuthenticated &&
    hasCompletedOnboarding &&
    (!desktopAccessIsCurrent ||
      (["unchecked", "checking"].includes(desktopAccess.status) &&
        !isRevalidatingAccess) ||
      (settledDesktopAccess && consent.status === "loading"));
  const { isAdmin: isOrgAdmin } = useIsOrgAdmin();
  const isAdmin = isOrgAdmin === true;
  useConsentAnalytics(
    hasCompletedOnboarding ? consent : { status: "loading" },
    isAdmin,
    "standalone_gate",
  );

  const spacesLayoutEnabled = useChannelsLayout();
  // Read through a ref so a flag arriving mid-startup cannot re-run the resolve and replace
  // a route the user has already moved off.
  const spacesLayoutEnabledRef = useRef(spacesLayoutEnabled);
  useEffect(() => {
    spacesLayoutEnabledRef.current = spacesLayoutEnabled;
  }, [spacesLayoutEnabled]);

  const readyForMainApp =
    isBootstrapped &&
    isAuthenticated &&
    hasCompletedOnboarding &&
    settledDesktopAccess &&
    consent.status === "resolved" &&
    consent.satisfied;
  const startupIdentity = getAuthIdentity(authState);

  useEffect(() => {
    if (consent.status !== "resolved" || !consent.satisfied) return;
    if (!startupIdentity || !authenticatedClient) return;
    void ensureSession(startupIdentity, authenticatedClient);
  }, [consent, startupIdentity, authenticatedClient]);

  // Resolve and load the initial route before mounting the router. Reset when
  // the user leaves the main app so a later re-entry starts fresh.
  const [initialRouteLoaded, setInitialRouteLoaded] = useState(false);
  useEffect(() => {
    if (!readyForMainApp) {
      setInitialRouteLoaded(false);
      return;
    }
    if (initialRouteLoaded) return;
    if (!startupIdentity || !authenticatedClient) return;

    let cancelled = false;
    const loadInitialRoute = async (): Promise<void> => {
      try {
        const { href, firstRun } = await resolveStartupLocation(
          startupIdentity,
          authenticatedClient,
          spacesLayoutEnabledRef.current,
        );
        if (firstRun) {
          showChannelList({ keepForRoute: firstRun.generalChannelId });
          useSpaceTreeStore.getState().expandSpace(firstRun.generalChannelId);
        }
        router.history.replace(href);
        rememberStartupLocation(startupIdentity, href);
        await router.load();
      } catch (error) {
        log.error("Failed to load initial route", { error });
      } finally {
        if (!cancelled) setInitialRouteLoaded(true);
      }
    };
    void loadInitialRoute();

    return () => {
      cancelled = true;
    };
  }, [
    readyForMainApp,
    initialRouteLoaded,
    startupIdentity,
    authenticatedClient,
  ]);

  useEffect(() => {
    if (!initialRouteLoaded || !startupIdentity) return;
    return router.history.subscribe(({ location }) => {
      rememberStartupLocation(startupIdentity, location.href);
    });
  }, [initialRouteLoaded, startupIdentity]);

  const mainRef = useRef<HTMLDivElement>(null);
  // Mirrors the "main" branch of renderContent() below; keep the two in sync.
  const showingMainApp = readyForMainApp && initialRouteLoaded;
  useAppVisibilityWatchdog(mainRef, showingMainApp);
  useAppLoadingGateTelemetry(showingMainApp, {
    isBootstrapped,
    isCheckingAccess,
    readyForMainApp,
    initialRouteLoaded,
    authStatus: authState.status,
    desktopAccessStatus: desktopAccess.status,
    desktopAccessIsCurrent,
    consentStatus: consent.status,
  });

  // Single gate for every state where the whole app is still loading.
  if (
    !isBootstrapped ||
    isCheckingAccess ||
    (readyForMainApp && !initialRouteLoaded)
  ) {
    return <AppLoadingScreen />;
  }

  // Which screen the app is on. The four pre-router screens render instead of
  // the RouterProvider, so anything the routed shell mounts is absent there.
  const activeScreen =
    !hasCompletedOnboarding && !isBlockedByAccessPolicy
      ? "onboarding"
      : !isAuthenticated
        ? "auth"
        : isBlockedByAccessPolicy
          ? "desktop-access"
          : consent.status === "error" || needsConsent
            ? "consent"
            : "main";

  const supportUrl = flindExternalUrl("support");
  const communityUrl = flindExternalUrl("community");
  const openSupport = supportUrl
    ? () => openExternalUrl(supportUrl)
    : undefined;
  const openCommunity = communityUrl
    ? () => openExternalUrl(communityUrl)
    : undefined;

  const renderContent = () => {
    if (activeScreen === "onboarding") {
      return (
        <motion.div
          key="onboarding"
          initial={{ opacity: 1 }}
          className="h-full"
        >
          <OnboardingFlow onOpenSupport={openCommunity} />
        </motion.div>
      );
    }

    if (activeScreen === "auth") {
      return (
        <motion.div key="auth" initial={{ opacity: 1 }} className="h-full">
          <AuthScreen onOpenSupport={openSupport} />
        </motion.div>
      );
    }

    if (activeScreen === "desktop-access") {
      return (
        <motion.div
          key="desktop-access"
          initial={{ opacity: 1 }}
          className="h-full"
        >
          <DesktopAccessScreen
            access={desktopAccess}
            orgProjectsMap={authState.orgProjectsMap}
            currentOrgId={authState.currentOrgId}
            currentProjectId={authState.currentProjectId}
            isSwitching={
              selectProjectMutation.isPending || switchOrgMutation.isPending
            }
            isRetrying={retryDesktopAccessMutation.isPending}
            isLoggingOut={logoutMutation.isPending}
            switchError={switchError}
            onSelectOrganization={(organizationId) =>
              switchOrgMutation.mutate(organizationId)
            }
            onSelectProject={(projectId) =>
              selectProjectMutation.mutate(projectId)
            }
            onRetry={() => retryDesktopAccessMutation.mutate()}
            onLogout={() => logoutMutation.mutate()}
            onOpenSupport={openSupport}
          />
        </motion.div>
      );
    }

    if (activeScreen === "consent") {
      return (
        <motion.div key="consent" initial={{ opacity: 1 }} className="h-full">
          <ConsentScreen
            banner={<UpdateBanner variant="compact" />}
            onOpenSupport={openCommunity}
            settingsDialog={<SettingsDialog />}
          />
        </motion.div>
      );
    }

    return (
      <motion.div key="main" ref={mainRef} className="app-fade-in h-full">
        <RouterProvider router={router} />
        {/* Surfaces a toast when a backgrounded canvas generation finishes,
            from anywhere in the app. Sibling of the router so it stays mounted
            across every route (not just the canvas space). Renders null. */}
        <CanvasGenerationToaster />
        <PendingPromptRecovery />
      </motion.div>
    );
  };

  const content = renderContent();

  return (
    <ToastProvider>
      <ErrorBoundary
        name="App"
        resetKey={authState.status}
        shouldSuppress={isNotAuthenticatedError}
      >
        <div className="flex h-screen flex-col">
          {/* The routed shell mounts its own banner at `__root`; the pre-router
              screens are outside the router, so they get it from here. */}
          {activeScreen !== "main" && <ConnectivityBanner />}
          <div className="relative min-h-0 flex-1 overflow-hidden">
            {isAuthenticated ? (
              <AnimatePresence mode="wait">{content}</AnimatePresence>
            ) : (
              content
            )}
            <ScopeReauthPrompt />
            <AddDirectoryDialog />
            <ErrorDetailsDialog />
            {isAuthenticated && <NewLoopDialog />}
            <UpdateAvailableModal />
            {isAuthenticated && <FeedbackHost />}
          </div>
          {devToolbar}
        </div>
      </ErrorBoundary>
    </ToastProvider>
  );
}

export default App;
