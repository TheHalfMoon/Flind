import type { GatewayLimitCause } from "@flind/shared";

export interface UsageLimitContent {
  title: string;
  description: string;
  actionLabel: string | null;
  dismissLabel: string;
}

export function usageLimitContent(args: {
  cause: GatewayLimitCause | null;
  resetLabel: string | null;
  subscribed: boolean | undefined;
  canManageBilling: boolean;
}): UsageLimitContent {
  const { cause, resetLabel, subscribed, canManageBilling } = args;

  if (cause === "model_gate") {
    if (!canManageBilling) {
      return {
        title: "This model isn't included",
        description:
          "Contact an organization administrator to add a payment method, or switch to an included model.",
        actionLabel: null,
        dismissLabel: "Got it",
      };
    }
    return {
      title: "Unlock premium models",
      description:
        "This model requires additional access. Review your organization's billing configuration or switch to an available model.",
      actionLabel: "Add payment method",
      dismissLabel: "Not now",
    };
  }

  if (cause === "model_unavailable") {
    return {
      title: "This model isn't available",
      description:
        "It's in preview and isn't turned on for your account yet. Pick another model to keep going.",
      actionLabel: null,
      dismissLabel: "Got it",
    };
  }

  if (cause === "user_limit") {
    return {
      title: "Usage limit reached",
      description:
        "You've reached a usage limit for now. Hourly model limits reset within the hour and daily limits after a day. Switch to a smaller model to keep working.",
      actionLabel: null,
      dismissLabel: "Got it",
    };
  }

  if (cause === "org_limit") {
    if (!canManageBilling) {
      return {
        title: "Organization usage limit reached",
        description:
          "Your organization has reached its configured usage limit. Contact an organization administrator to change the limit.",
        actionLabel: null,
        dismissLabel: "Got it",
      };
    }
    if (subscribed === false) {
      return {
        title: "Free usage used up",
        description: `Your organization has used up its included usage.${
          resetLabel ? ` ${resetLabel}.` : ""
        } Review your organization's billing configuration before continuing.`,
        actionLabel: "Add payment method",
        dismissLabel: "Not now",
      };
    }
    return {
      title: "Organization usage limit reached",
      description:
        "Your organization has reached its configured usage limit. Change the limit in Plan & usage to keep going.",
      actionLabel: "Open Plan & usage",
      dismissLabel: "Got it",
    };
  }

  // Not a billing denial (e.g. an upstream provider's own rate limit) —
  // don't send the user to billing for something billing can't fix.
  return {
    title: "Usage limit reached",
    description: `This app hit a usage limit.${
      resetLabel ? ` ${resetLabel}.` : ""
    } Please try again shortly.`,
    actionLabel: null,
    dismissLabel: "Got it",
  };
}
