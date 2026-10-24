import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { UsageLimitModalContent } from "./UsageLimitModal";

const content = {
  title: "Flind usage limit",
  description: "Review the current usage limits.",
  actionLabel: "Add payment method",
  dismissLabel: "Not now",
};

describe("Flind first-party billing containment", () => {
  it("does not offer a nonfunctional payment CTA without an approved billing URL", async () => {
    const onAction = vi.fn();
    const onDismiss = vi.fn();
    render(
      <UsageLimitModalContent
        open
        content={content}
        onAction={onAction}
        onDismiss={onDismiss}
        actionAvailable={false}
      />,
    );
    expect(
      screen.getByText(
        "Flind billing is not configured for this installation.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Add payment method" }),
    ).toBeNull();
    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: "Not now" }));
    expect(onDismiss).toHaveBeenCalledOnce();
    expect(onAction).not.toHaveBeenCalled();
  });

  it("only exposes the billing action with an explicit qualified destination", async () => {
    const onAction = vi.fn();
    const onDismiss = vi.fn();
    render(
      <UsageLimitModalContent
        open
        content={content}
        onAction={onAction}
        onDismiss={onDismiss}
        actionAvailable
      />,
    );
    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: "Add payment method" }));
    expect(onAction).toHaveBeenCalledOnce();
    expect(onDismiss).not.toHaveBeenCalled();
  });
});
