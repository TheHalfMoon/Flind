import {
  ArrowClockwise,
  CaretDown,
  Coins,
  HourglassMedium,
  RocketLaunch,
  SignOut,
  WarningCircle,
} from "@phosphor-icons/react";
import type { DesktopAccess, OrgProjectsMap } from "@flind/core/auth/schemas";
import {
  Button,
  Combobox,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxInput,
  ComboboxItem,
  ComboboxList,
  ComboboxTrigger,
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
  Field,
  FieldLabel,
} from "@flind/quill";
import { ANALYTICS_EVENTS } from "@flind/shared/analytics-events";
import { FullScreenLayout } from "@flind/ui/primitives/FullScreenLayout";
import { Spinner } from "@flind/ui/primitives/Spinner";
import { track } from "@flind/ui/shell/analytics";
import {
  FIELD_CONTENT_CLASS,
  FIELD_TRIGGER_CLASS,
} from "@flind/ui/styles/fieldTrigger";
import { useEffect, useMemo, useRef, useState } from "react";

interface OrganizationOption {
  id: string;
  name: string;
}

interface ProjectOption {
  id: number;
  name: string;
}

const BLOCKED_CONTENT = {
  startup_plan: {
    icon: <RocketLaunch />,
    title: "Flind Desktop access is restricted",
    description:
      "This organization's access is restricted by the server policy. Select another organization or ask an administrator to review access.",
  },
  prepaid_credits: {
    icon: <Coins />,
    title: "Flind Desktop access is restricted",
    description:
      "This organization's access is restricted by the server policy. Select another organization or ask an administrator to review access.",
  },
} as const;

// A null reason is the server's compatibility signal for paused sign-ups.
const SIGNUPS_PAUSED_CONTENT = {
  icon: <HourglassMedium />,
  title: "Flind Desktop sign-ups are paused",
  description:
    "New access is unavailable right now. Select another organization or check again later.",
};

interface DesktopAccessScreenProps {
  access: DesktopAccess;
  orgProjectsMap: OrgProjectsMap;
  currentOrgId: string | null;
  currentProjectId: number | null;
  isSwitching: boolean;
  isRetrying: boolean;
  isLoggingOut: boolean;
  switchError: string | null;
  onSelectOrganization: (organizationId: string) => void;
  onSelectProject: (projectId: number) => void;
  onRetry: () => void;
  onLogout: () => void;
  onOpenSupport?: () => void;
}

export function DesktopAccessScreen({
  access,
  orgProjectsMap,
  currentOrgId,
  currentProjectId,
  isSwitching,
  isRetrying,
  isLoggingOut,
  switchError,
  onSelectOrganization,
  onSelectProject,
  onRetry,
  onLogout,
  onOpenSupport,
}: DesktopAccessScreenProps) {
  const [organizationOpen, setOrganizationOpen] = useState(false);
  const [projectOpen, setProjectOpen] = useState(false);
  const organizationAnchorRef = useRef<HTMLButtonElement>(null);
  const projectAnchorRef = useRef<HTMLButtonElement>(null);

  const organizations = useMemo<OrganizationOption[]>(
    () =>
      Object.entries(orgProjectsMap)
        .map(([id, organization]) => ({ id, name: organization.orgName }))
        .sort((first, second) => first.name.localeCompare(second.name)),
    [orgProjectsMap],
  );
  const projects = useMemo<ProjectOption[]>(
    () =>
      (currentOrgId
        ? (orgProjectsMap[currentOrgId]?.projects ?? [])
        : []
      ).toSorted((first, second) => first.name.localeCompare(second.name)),
    [currentOrgId, orgProjectsMap],
  );
  const selectedOrganization =
    organizations.find((organization) => organization.id === currentOrgId) ??
    null;
  const selectedProject =
    projects.find((project) => project.id === currentProjectId) ?? null;
  const controlsDisabled = isSwitching || access.status === "checking";

  useEffect(() => {
    if (access.status !== "blocked" && access.status !== "error") return;
    track(ANALYTICS_EVENTS.DESKTOP_ACCESS_SCREEN_SHOWN, {
      status: access.status,
      reason: access.reason,
    });
  }, [access.status, access.reason]);

  const blockedContent = access.reason
    ? BLOCKED_CONTENT[access.reason]
    : SIGNUPS_PAUSED_CONTENT;
  const isTechnicalError = access.status === "error";
  const icon = isTechnicalError ? <WarningCircle /> : blockedContent?.icon;
  const title = isTechnicalError
    ? "Couldn't check Desktop access"
    : blockedContent?.title;
  const description = isTechnicalError
    ? "Try again, or select another organization or project."
    : blockedContent?.description;
  const isSignupsPaused = access.status === "blocked" && !access.reason;

  const footerRight = (
    <Button
      variant="link-muted"
      size="sm"
      loading={isLoggingOut}
      disabled={isLoggingOut || isSwitching || isRetrying}
      onClick={onLogout}
      data-attr="desktop-access-logout"
    >
      <SignOut />
      Log out
    </Button>
  );

  return (
    <FullScreenLayout footerRight={footerRight} onOpenSupport={onOpenSupport}>
      <div className="h-full overflow-y-auto px-8 py-20">
        <div className="flex min-h-full items-center justify-center">
          <Empty className="w-full max-w-xl">
            <EmptyHeader>
              <EmptyMedia variant="icon">{icon}</EmptyMedia>
              <EmptyTitle>{title}</EmptyTitle>
              <EmptyDescription
                className={
                  isSignupsPaused ? "text-destructive-foreground" : undefined
                }
              >
                {isSignupsPaused && (
                  <WarningCircle
                    aria-hidden="true"
                    className="mr-1 inline-block align-text-bottom"
                  />
                )}
                {description}
              </EmptyDescription>
            </EmptyHeader>
            <EmptyContent className="w-full max-w-md gap-4">
              <div className="flex w-full flex-col gap-4">
                <Field className="min-w-0">
                  <FieldLabel htmlFor="desktop-access-organization">
                    Organization
                  </FieldLabel>
                  <Combobox<OrganizationOption>
                    items={organizations}
                    value={selectedOrganization}
                    onValueChange={(value) => {
                      if (value && value.id !== currentOrgId) {
                        onSelectOrganization(value.id);
                      }
                      setOrganizationOpen(false);
                    }}
                    open={organizationOpen}
                    onOpenChange={setOrganizationOpen}
                    itemToStringLabel={(organization) => organization.name}
                    itemToStringValue={(organization) => organization.id}
                    disabled={controlsDisabled}
                  >
                    <ComboboxTrigger
                      nativeButton
                      render={
                        <button
                          ref={organizationAnchorRef}
                          id="desktop-access-organization"
                          type="button"
                          className={FIELD_TRIGGER_CLASS}
                          data-attr="desktop-access-organization-switcher"
                        >
                          <span className="min-w-0 flex-1 truncate text-left">
                            {selectedOrganization?.name ??
                              "Select organization"}
                          </span>
                          {isSwitching ? (
                            <Spinner />
                          ) : (
                            <CaretDown
                              size={14}
                              className="shrink-0 text-muted"
                            />
                          )}
                        </button>
                      }
                    />
                    <ComboboxContent
                      anchor={organizationAnchorRef}
                      side="bottom"
                      align="start"
                      sideOffset={4}
                      className={FIELD_CONTENT_CLASS}
                    >
                      <ComboboxInput
                        placeholder="Search organizations..."
                        showTrigger={false}
                      />
                      <ComboboxEmpty>No organizations found.</ComboboxEmpty>
                      <ComboboxList>
                        {(organization: OrganizationOption) => (
                          <ComboboxItem
                            key={organization.id}
                            value={organization}
                          >
                            {organization.name}
                          </ComboboxItem>
                        )}
                      </ComboboxList>
                    </ComboboxContent>
                  </Combobox>
                </Field>

                <Field className="min-w-0">
                  <FieldLabel htmlFor="desktop-access-project">
                    Project
                  </FieldLabel>
                  <Combobox<ProjectOption>
                    items={projects}
                    value={selectedProject}
                    onValueChange={(value) => {
                      if (value && value.id !== currentProjectId) {
                        onSelectProject(value.id);
                      }
                      setProjectOpen(false);
                    }}
                    open={projectOpen}
                    onOpenChange={setProjectOpen}
                    itemToStringLabel={(project) => project.name}
                    itemToStringValue={(project) => String(project.id)}
                    disabled={controlsDisabled}
                  >
                    <ComboboxTrigger
                      nativeButton
                      render={
                        <button
                          ref={projectAnchorRef}
                          id="desktop-access-project"
                          type="button"
                          className={FIELD_TRIGGER_CLASS}
                          data-attr="desktop-access-project-switcher"
                        >
                          <span className="min-w-0 flex-1 truncate text-left">
                            {selectedProject?.name ?? "Select project"}
                          </span>
                          {isSwitching ? (
                            <Spinner />
                          ) : (
                            <CaretDown
                              size={14}
                              className="shrink-0 text-muted"
                            />
                          )}
                        </button>
                      }
                    />
                    <ComboboxContent
                      anchor={projectAnchorRef}
                      side="bottom"
                      align="start"
                      sideOffset={4}
                      className={FIELD_CONTENT_CLASS}
                    >
                      <ComboboxInput
                        placeholder="Search projects..."
                        showTrigger={false}
                      />
                      <ComboboxEmpty>No projects found.</ComboboxEmpty>
                      <ComboboxList>
                        {(project: ProjectOption) => (
                          <ComboboxItem key={project.id} value={project}>
                            {project.name}
                          </ComboboxItem>
                        )}
                      </ComboboxList>
                    </ComboboxContent>
                  </Combobox>
                </Field>
              </div>

              {switchError && (
                <p role="alert" className="text-destructive text-sm">
                  {switchError}
                </p>
              )}

              <Button
                variant={isSignupsPaused ? "outline" : "primary"}
                loading={isRetrying}
                disabled={isRetrying || isSwitching}
                onClick={onRetry}
                data-attr="desktop-access-retry"
              >
                <ArrowClockwise />
                {isTechnicalError ? "Try again" : "Check again"}
              </Button>
            </EmptyContent>
          </Empty>
        </div>
      </div>
    </FullScreenLayout>
  );
}
