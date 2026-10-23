import client from "posthog-js";

const apiKey = import.meta.env.VITE_FLIND_ANALYTICS_API_KEY;
const apiHost = import.meta.env.VITE_FLIND_ANALYTICS_HOST;

export function initAnalytics(): void {
  if (!apiKey || !apiHost) return;
  client.init(apiKey, {
    api_host: apiHost,
    ui_host: import.meta.env.VITE_FLIND_ANALYTICS_UI_HOST || apiHost,
    autocapture: false,
    capture_pageview: false,
    capture_pageleave: false,
    disable_session_recording: true,
  });
}

export function capture(
  event: string,
  properties?: Record<string, unknown>,
): void {
  if (!apiKey || !apiHost) return;
  client.capture(event, properties);
}

export function captureException(error: unknown): void {
  if (!apiKey || !apiHost) return;
  client.captureException(error);
}

export function identify(distinctId: string, label?: string): void {
  if (!apiKey || !apiHost) return;
  client.identify(distinctId, label ? { name: label } : undefined);
}
