import { createElement } from "react";
import { act, create } from "react-test-renderer";
import { describe, expect, it } from "vitest";
import { ConsentPanel } from "./ConsentPanel";

type Renderer = NonNullable<ReturnType<typeof create>>;

function render(props: Partial<Parameters<typeof ConsentPanel>[0]> = {}) {
  let renderer!: Renderer;
  act(() => {
    renderer = create(
      createElement(ConsentPanel, {
        organizationName: "Flind test organization",
        needsAiConsent: true,
        needsBetaTerms: false,
        isAdmin: true,
        ...props,
      }),
    );
  });
  return renderer;
}

function texts(renderer: Renderer): string[] {
  return renderer.root
    .findAll((node) => typeof node.props.children === "string")
    .map((node) => node.props.children as string);
}

function clickableControls(renderer: Renderer) {
  return renderer.root.findAll(
    (node) => typeof node.props.onPress === "function",
  );
}

describe("ConsentPanel legal qualification containment", () => {
  it("tells the administrator the Flind AI approval cannot be submitted", () => {
    const renderer = render({ isAdmin: true, needsAiConsent: true });
    const content = texts(renderer);
    expect(content).toContain("Flind consent review required");
    expect(content).toContain("AI data-processing approval unavailable");
    expect(content).not.toContain("Approve AI data processing");
    expect(clickableControls(renderer)).toHaveLength(0);
  });

  it("explains why beta terms cannot be accepted", () => {
    const renderer = render({
      needsAiConsent: false,
      needsBetaTerms: true,
    });
    const content = texts(renderer);
    expect(content).toContain("Flind beta terms unavailable");
    expect(content.join(" ")).not.toContain("PostHog");
    expect(content.join(" ")).not.toContain("Baseten");
    expect(content.join(" ")).not.toContain("Modal");
    expect(clickableControls(renderer)).toHaveLength(0);
  });

  it("handles both outstanding flags without an external link or approval", () => {
    const renderer = render({
      needsAiConsent: true,
      needsBetaTerms: true,
    });
    const content = texts(renderer);
    expect(content).toContain("AI data-processing approval unavailable");
    expect(content).toContain("Flind beta terms unavailable");
    expect(clickableControls(renderer)).toHaveLength(0);
  });

  it("directs non-admins to their organization administrator", () => {
    const renderer = render({ isAdmin: false });
    expect(texts(renderer).join(" ")).toContain(
      "Contact an organization administrator",
    );
    expect(clickableControls(renderer)).toHaveLength(0);
  });

  it("uses generic copy without an organization name", () => {
    const renderer = render({ organizationName: undefined });
    expect(texts(renderer).join(" ")).toContain(
      "This organization cannot proceed",
    );
    expect(clickableControls(renderer)).toHaveLength(0);
  });
});
