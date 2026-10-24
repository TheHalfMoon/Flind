import { ANALYTICS_EVENTS } from "@flind/shared/analytics-events";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DesktopAccessScreen } from "./DesktopAccessScreen";

const { track } = vi.hoisted(() => ({ track: vi.fn() }));
vi.mock("@flind/ui/shell/analytics", () => ({ track }));
const orgProjectsMap = {
  "org-1": {
    orgName: "First organization",
    projects: [
      { id: 1, name: "Website" },
      { id: 2, name: "Mobile app" },
    ],
  },
  "org-2": {
    orgName: "Second organization",
    projects: [{ id: 3, name: "Product" }],
  },
};

function renderScreen(
  access:
    | {
        projectId: number;
        status: "blocked";
        reason: "startup_plan" | "prepaid_credits" | null;
      }
    | { projectId: number; status: "error"; reason: null },
) {
  const onSelectOrganization = vi.fn();
  const onSelectProject = vi.fn();
  const onRetry = vi.fn();
  const onLogout = vi.fn();
  const onOpenSupport = vi.fn();
  const result = render(
    <DesktopAccessScreen
      access={access}
      orgProjectsMap={orgProjectsMap}
      currentOrgId="org-1"
      currentProjectId={1}
      isSwitching={false}
      isRetrying={false}
      isLoggingOut={false}
      switchError={null}
      onSelectOrganization={onSelectOrganization}
      onSelectProject={onSelectProject}
      onRetry={onRetry}
      onLogout={onLogout}
      onOpenSupport={onOpenSupport}
    />,
  );
  return {
    ...result,
    onSelectOrganization,
    onSelectProject,
    onRetry,
    onLogout,
    onOpenSupport,
  };
}

describe("DesktopAccessScreen", () => {
  it.each([
    ["startup_plan", "access is restricted by the server policy"],
    ["prepaid_credits", "access is restricted by the server policy"],
    [null, "New access is unavailable right now"],
  ] as const)("renders the %s reason", (reason, expectedCopy) => {
    track.mockClear();
    renderScreen({ projectId: 1, status: "blocked", reason });

    expect(screen.getByText(new RegExp(expectedCopy))).toBeInTheDocument();
    expect(track).toHaveBeenCalledExactlyOnceWith(
      ANALYTICS_EVENTS.DESKTOP_ACCESS_SCREEN_SHOWN,
      { status: "blocked", reason },
    );
    expect(screen.getByText("First organization")).toBeInTheDocument();
    expect(screen.getByText("Website")).toBeInTheDocument();
  });

  it.each([
    [{ projectId: 1, status: "error", reason: null }, "Try again"],
    [
      { projectId: 1, status: "blocked", reason: "startup_plan" },
      "Check again",
    ],
  ] as const)("rechecks access for %s", async (access, buttonLabel) => {
    const user = userEvent.setup();
    const { onRetry } = renderScreen(access);

    await user.click(screen.getByText(buttonLabel));

    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("does not show inherited vendor games or sales links when sign-ups are paused", () => {
    const { container } = renderScreen({
      projectId: 1,
      status: "blocked",
      reason: null,
    });
    expect(
      screen.getByText("Flind Desktop sign-ups are paused"),
    ).toBeInTheDocument();
    expect(container.textContent).not.toContain("PostHog");
    expect(container.textContent).not.toContain("hedgehog");
    expect(container.querySelector('a[href*="posthog.com"]')).toBeNull();
    expect(screen.queryByRole("button", { name: /game/i })).toBeNull();
  });

  it("does not expose vendor sales or external URLs for prepaid credit restrictions", () => {
    const { container } = renderScreen({
      projectId: 1,
      status: "blocked",
      reason: "prepaid_credits",
    });
    expect(container.textContent).not.toContain("sales@");
    expect(container.textContent).not.toContain("PostHog");
    expect(container.querySelector('a[href*="posthog.com"]')).toBeNull();
  });

  it("lets the user select another project", async () => {
    const user = userEvent.setup();
    const { container, onSelectProject } = renderScreen({
      projectId: 1,
      status: "blocked",
      reason: "startup_plan",
    });
    const trigger = container.querySelector(
      '[data-attr="desktop-access-project-switcher"]',
    );
    expect(trigger).not.toBeNull();

    await user.click(trigger as HTMLElement);
    await user.click(await screen.findByText("Mobile app"));

    expect(onSelectProject).toHaveBeenCalledWith(2);
  });

  it("lets the user select another organization and log out", async () => {
    const user = userEvent.setup();
    const { container, onSelectOrganization, onLogout, onOpenSupport } =
      renderScreen({
        projectId: 1,
        status: "blocked",
        reason: "prepaid_credits",
      });
    const trigger = container.querySelector(
      '[data-attr="desktop-access-organization-switcher"]',
    );
    expect(trigger).not.toBeNull();

    await user.click(trigger as HTMLElement);
    await user.click(await screen.findByText("Second organization"));
    await user.click(screen.getByText("Get support"));
    await user.click(screen.getByText("Log out"));

    expect(onSelectOrganization).toHaveBeenCalledWith("org-2");
    expect(onOpenSupport).toHaveBeenCalledOnce();
    expect(onLogout).toHaveBeenCalledOnce();
  });
});
