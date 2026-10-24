import type {
  InstallCustomMcpServerOptions,
  InstallMcpTemplateOptions,
  McpInstallResponse,
  McpServerInstallation,
} from "@flind/api-client/types";
import * as Linking from "expo-linking";
import * as WebBrowser from "expo-web-browser";
import { getPostHogApiClient } from "@/lib/posthogApiClient";
import { isMcpOAuthRedirect } from "./presentation";

/** Custom URL scheme registered via app.json (`scheme: "flind"`). The cloud
 *  bounces the OAuth redirect back to this URL once the provider completes
 *  auth, and `expo-linking` catches it on both iOS and Android. */
export const OAUTH_CALLBACK_URL = "flind://mcp-oauth/callback";

const INSTALL_SOURCE = "posthog-code" as const;

/** Direct installation row or the status of an OAuth redirect handshake. */
export type McpOAuthInstallResult =
  | McpServerInstallation
  | "completed"
  | "cancelled";

/** Verify the actual deep-link destination, not merely Expo's success flag.
 *  Ignore errors, unexpected paths, and same-prefix lookalike callbacks. */
export function isSuccessfulMcpOAuthCallback(value: string): boolean {
  try {
    const url = new URL(value);
    return (
      url.protocol === "flind:" &&
      url.hostname === "mcp-oauth" &&
      url.pathname === "/callback" &&
      !url.searchParams.has("error")
    );
  } catch {
    return false;
  }
}

/**
 * Open the cloud-provided redirect URL in the system browser and wait for the
 * user to complete the OAuth dance. Resolves once the cloud bounces the
 * callback back to `OAUTH_CALLBACK_URL`, or once the user dismisses the
 * browser without completing.
 */
async function waitForOAuthCallback(
  redirectUrl: string,
): Promise<"completed" | "cancelled"> {
  // `openAuthSessionAsync` automatically dismisses the browser sheet on the
  // first incoming deep link matching our scheme — handy for OAuth on both
  // iOS (ASWebAuthenticationSession) and Android (Custom Tabs).
  const result = await WebBrowser.openAuthSessionAsync(
    redirectUrl,
    OAUTH_CALLBACK_URL,
  );

  return result.type === "success" && isSuccessfulMcpOAuthCallback(result.url)
    ? "completed"
    : "cancelled";
}

/**
 * Run the install flow for a marketplace template. If the cloud responds with
 * an OAuth redirect, take the user through it and resolve once they're back.
 */
export async function installTemplateWithOAuth(
  options: Omit<
    InstallMcpTemplateOptions,
    "install_source" | "posthog_code_callback_url"
  >,
): Promise<McpOAuthInstallResult> {
  const response: McpInstallResponse =
    await getPostHogApiClient().installMcpTemplate({
      ...options,
      install_source: INSTALL_SOURCE,
      posthog_code_callback_url: OAUTH_CALLBACK_URL,
    });

  if (!isMcpOAuthRedirect(response)) return response;

  const outcome = await waitForOAuthCallback(response.redirect_url);
  if (outcome === "cancelled") return "cancelled";

  // Callback received; the cloud holds the installation record.
  // The caller must refetch instead of incorrectly treating it as cancelled.
  return "completed";
}

/** Same as install-template, for custom servers. */
export async function installCustomWithOAuth(
  options: Omit<
    InstallCustomMcpServerOptions,
    "install_source" | "posthog_code_callback_url"
  >,
): Promise<McpOAuthInstallResult> {
  const response: McpInstallResponse =
    await getPostHogApiClient().installCustomMcpServer({
      ...options,
      install_source: INSTALL_SOURCE,
      posthog_code_callback_url: OAUTH_CALLBACK_URL,
    });

  if (!isMcpOAuthRedirect(response)) return response;
  const outcome = await waitForOAuthCallback(response.redirect_url);
  return outcome;
}

/**
 * Trigger a re-auth flow for an installation whose OAuth token has expired
 * (cloud sets `needs_reauth: true`). Opens the cloud's authorize endpoint,
 * which returns a redirect URL, then runs the same WebBrowser session.
 */
export async function reauthorizeInstallation(
  installationId: string,
): Promise<"completed" | "cancelled"> {
  const { redirect_url } = await getPostHogApiClient().authorizeMcpInstallation(
    {
      installation_id: installationId,
      install_source: INSTALL_SOURCE,
      posthog_code_callback_url: OAUTH_CALLBACK_URL,
    },
  );
  return waitForOAuthCallback(redirect_url);
}

/** Subscribe to deep-link events for the OAuth callback. Mainly useful when
 *  the WebBrowser session can't auto-dismiss for some reason. */
export function onOAuthCallback(handler: (url: string) => void): {
  remove(): void;
} {
  const subscription = Linking.addEventListener("url", ({ url }) => {
    if (isSuccessfulMcpOAuthCallback(url)) handler(url);
  });
  return subscription;
}
