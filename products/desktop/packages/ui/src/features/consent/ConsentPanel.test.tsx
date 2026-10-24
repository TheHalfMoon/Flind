import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ConsentPanel } from "./ConsentPanel";

const mutation = vi.hoisted(() => ({
  approveAiDataProcessing: vi.fn(),
  acceptDesktopBetaTerms: vi.fn(),
}));

vi.mock("@flind/ui/features/auth/authClient", () => ({
  useAuthenticatedClient: () => mutation,
}));

function renderPanel(
  needsAiConsent: boolean,
  needsBetaTerms: boolean,
  isAdmin = true,
  requirements?: { needsAiConsent: boolean; needsBetaTerms: boolean },
  retry = vi.fn().mockResolvedValue(undefined),
) {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConsentPanel
        consent={{
          status: "resolved",
          organizationId: "org-id",
          needsAiConsent,
          needsBetaTerms,
          satisfied: !needsAiConsent && !needsBetaTerms,
          retry,
        }}
        requirements={requirements}
        isAdmin={isAdmin}
      />
    </QueryClientProvider>,
  );
}

describe("Flind Desktop legal consent containment", () => {
  beforeEach(() => {
    mutation.approveAiDataProcessing.mockReset();
    mutation.acceptDesktopBetaTerms.mockReset();
  });

  it("renders only Flind beta qualification with no acceptance controls", () => {
    renderPanel(false, true);
    expect(
      screen.getByText("Flind beta terms unavailable"),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("AI data-processing approval unavailable"),
    ).toBeNull();
    expect(
      screen.queryByRole("button", { name: "Accept beta terms" }),
    ).toBeNull();
    expect(screen.queryByRole("link")).toBeNull();
    expect(mutation.acceptDesktopBetaTerms).not.toHaveBeenCalled();
  });

  it("shows both outstanding requirements without old subprocessor or HIPAA promises", () => {
    const { container } = renderPanel(true, true);
    expect(
      screen.getByText("AI data-processing approval unavailable"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Flind beta terms unavailable"),
    ).toBeInTheDocument();
    for (const forbidden of [
      "PostHog",
      "Baseten",
      "Modal",
      "HIPAA",
      "PHI",
      "subprocessors",
    ]) {
      expect(container.textContent).not.toContain(forbidden);
    }
    expect(screen.getAllByRole("button")).toHaveLength(1); // Refresh only
  });

  it("does not consider historic acceptance a new Flind approval flow", () => {
    renderPanel(false, false, true, {
      needsAiConsent: true,
      needsBetaTerms: true,
    });
    expect(screen.getAllByRole("button")).toHaveLength(1);
    expect(screen.queryByText("Accepted")).toBeNull();
  });

  it("directs members to the administrator without old vendor links", () => {
    renderPanel(true, true, false);
    expect(
      screen.getByText(/Contact an organization administrator/),
    ).toBeInTheDocument();
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("refreshes server state without mutating consent decisions", async () => {
    const retry = vi.fn().mockResolvedValue(undefined);
    renderPanel(true, false, true, undefined, retry);
    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: "Refresh" }));
    await waitFor(() => expect(retry).toHaveBeenCalledOnce());
    expect(mutation.approveAiDataProcessing).not.toHaveBeenCalled();
    expect(mutation.acceptDesktopBetaTerms).not.toHaveBeenCalled();
  });

  it("shows a local status error when retry fails", async () => {
    const retry = vi.fn().mockRejectedValue(new Error("network"));
    renderPanel(true, false, true, undefined, retry);
    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: "Refresh" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not refresh Flind consent status",
    );
  });
});
