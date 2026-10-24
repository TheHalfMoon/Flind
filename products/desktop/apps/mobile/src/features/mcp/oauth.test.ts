import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  openAuthSessionAsync: vi.fn(),
  installMcpTemplate: vi.fn(),
  installCustomMcpServer: vi.fn(),
  authorizeMcpInstallation: vi.fn(),
  addEventListener: vi.fn(),
}));

vi.mock("expo-web-browser", () => ({
  openAuthSessionAsync: mocks.openAuthSessionAsync,
}));
vi.mock("expo-linking", () => ({ addEventListener: mocks.addEventListener }));
vi.mock("@/lib/posthogApiClient", () => ({
  getPostHogApiClient: () => ({
    installMcpTemplate: mocks.installMcpTemplate,
    installCustomMcpServer: mocks.installCustomMcpServer,
    authorizeMcpInstallation: mocks.authorizeMcpInstallation,
  }),
}));

import {
  installCustomWithOAuth,
  installTemplateWithOAuth,
  isSuccessfulMcpOAuthCallback,
  OAUTH_CALLBACK_URL,
  onOAuthCallback,
  reauthorizeInstallation,
} from "./oauth";

const redirect = "https://login.example.org/oauth/authorize";
const successUrl = OAUTH_CALLBACK_URL + "?code=abc123";

beforeEach(() => {
  vi.resetAllMocks();
});

describe("MCP OAuth callback validation", () => {
  it.each([
    [OAUTH_CALLBACK_URL, true],
    [successUrl, true],
    [OAUTH_CALLBACK_URL + "#ready", true],
    [OAUTH_CALLBACK_URL + "?error=access_denied", false],
    ["flind://mcp-oauth/callback-malicious", false],
    ["flind://mcp-oauth/other", false],
    ["flind://other/callback", false],
    ["https://mcp-oauth/callback", false],
    ["not a URL", false],
  ])("recognizes exact callback shape %s", (url, expected) => {
    expect(isSuccessfulMcpOAuthCallback(url)).toBe(expected);
  });

  it("notifies listeners only for expected, non-error callbacks", () => {
    const remove = vi.fn();
    const handler = vi.fn();
    mocks.addEventListener.mockReturnValue({ remove });
    const sub = onOAuthCallback(handler);
    expect(mocks.addEventListener).toHaveBeenCalledWith(
      "url",
      expect.any(Function),
    );
    const listener = mocks.addEventListener.mock.calls[0][1] as (e: {
      url: string;
    }) => void;

    listener({ url: "flind://mcp-oauth/callback-malicious" });
    listener({ url: OAUTH_CALLBACK_URL + "?error=denied" });
    expect(handler).not.toHaveBeenCalled();
    listener({ url: successUrl });
    expect(handler).toHaveBeenCalledOnce();
    expect(handler).toHaveBeenCalledWith(successUrl);
    sub.remove();
    expect(remove).toHaveBeenCalledOnce();
  });
});

describe("MCP installation OAuth outcomes", () => {
  it("returns the direct installed template without opening the browser", async () => {
    const installation = { id: "inst-1", name: "Flind MCP" };
    mocks.installMcpTemplate.mockResolvedValue(installation);
    expect(
      await installTemplateWithOAuth({ template_id: "template-1" }),
    ).toEqual(installation);
    expect(mocks.openAuthSessionAsync).not.toHaveBeenCalled();
  });

  it("returns completed after a valid template OAuth callback", async () => {
    mocks.installMcpTemplate.mockResolvedValue({ redirect_url: redirect });
    mocks.openAuthSessionAsync.mockResolvedValue({
      type: "success",
      url: successUrl,
    });
    expect(await installTemplateWithOAuth({ template_id: "template-1" })).toBe(
      "completed",
    );
    expect(mocks.installMcpTemplate).toHaveBeenCalledWith({
      template_id: "template-1",
      install_source: "posthog-code",
      posthog_code_callback_url: OAUTH_CALLBACK_URL,
    });
    expect(mocks.openAuthSessionAsync).toHaveBeenCalledWith(
      redirect,
      OAUTH_CALLBACK_URL,
    );
  });

  it("returns cancelled when a template OAuth session is dismissed", async () => {
    mocks.installMcpTemplate.mockResolvedValue({ redirect_url: redirect });
    mocks.openAuthSessionAsync.mockResolvedValue({ type: "cancel" });
    expect(await installTemplateWithOAuth({ template_id: "template-1" })).toBe(
      "cancelled",
    );
  });

  it("does not report completion for unexpected or errored callbacks", async () => {
    mocks.installMcpTemplate.mockResolvedValue({ redirect_url: redirect });
    for (const url of [
      "flind://mcp-oauth/callback-malicious",
      OAUTH_CALLBACK_URL + "?error=denied",
      "https://other.example.com/callback",
    ]) {
      mocks.openAuthSessionAsync.mockResolvedValue({ type: "success", url });
      expect(
        await installTemplateWithOAuth({ template_id: "template-1" }),
      ).toBe("cancelled");
    }
  });

  it("preserves a successful custom-server OAuth result", async () => {
    mocks.installCustomMcpServer.mockResolvedValue({ redirect_url: redirect });
    mocks.openAuthSessionAsync.mockResolvedValue({
      type: "success",
      url: successUrl,
    });
    expect(
      await installCustomWithOAuth({
        name: "Flind local",
        url: "https://mcp.example.org",
        auth_type: "oauth",
      }),
    ).toBe("completed");
    expect(mocks.installCustomMcpServer).toHaveBeenCalledWith(
      expect.objectContaining({
        install_source: "posthog-code",
        posthog_code_callback_url: OAUTH_CALLBACK_URL,
      }),
    );
  });

  it("preserves a cancelled custom-server OAuth result", async () => {
    mocks.installCustomMcpServer.mockResolvedValue({ redirect_url: redirect });
    mocks.openAuthSessionAsync.mockResolvedValue({ type: "cancel" });
    expect(
      await installCustomWithOAuth({
        name: "Flind local",
        url: "https://mcp.example.org",
        auth_type: "oauth",
      }),
    ).toBe("cancelled");
  });

  it("uses the same callback validation when reauthorizing", async () => {
    mocks.authorizeMcpInstallation.mockResolvedValue({
      redirect_url: redirect,
    });
    mocks.openAuthSessionAsync.mockResolvedValue({
      type: "success",
      url: successUrl,
    });
    expect(await reauthorizeInstallation("installation-1")).toBe("completed");
    expect(mocks.authorizeMcpInstallation).toHaveBeenCalledWith({
      installation_id: "installation-1",
      install_source: "posthog-code",
      posthog_code_callback_url: OAUTH_CALLBACK_URL,
    });
  });

  it("propagates API failures rather than reporting success", async () => {
    mocks.installMcpTemplate.mockRejectedValue(new Error("backend failure"));
    await expect(
      installTemplateWithOAuth({ template_id: "template-1" }),
    ).rejects.toThrow("backend failure");
  });
});
