import { normalizeCustomCloud, type CustomCloud } from "./custom-cloud";
import type { CloudRegion } from "./regions";

type HostedRegion = Extract<CloudRegion, "us" | "eu" | "dev-cloud">;

const ENV_KEYS: Record<HostedRegion, { url: string; oauthClientId: string }> = {
  us: {
    url: "FLIND_US_CLOUD_URL",
    oauthClientId: "FLIND_US_OAUTH_CLIENT_ID",
  },
  eu: {
    url: "FLIND_EU_CLOUD_URL",
    oauthClientId: "FLIND_EU_OAUTH_CLIENT_ID",
  },
  "dev-cloud": {
    url: "FLIND_DEV_CLOUD_URL",
    oauthClientId: "FLIND_DEV_CLOUD_OAUTH_CLIENT_ID",
  },
};

function readPublicConfig(name: string): string | undefined {
  const valueFromProcess =
    typeof process !== "undefined" ? process.env?.[name] : undefined;
  if (valueFromProcess?.trim()) return valueFromProcess;
  // These contain public endpoints and OAuth client *IDs*, never secrets.
  const meta = import.meta as ImportMeta & {
    env?: Record<string, string | undefined>;
  };
  return meta.env?.["VITE_" + name];
}

/** The hosted regions are compatibility region IDs, not authorization to
 * send users, bearer tokens or OAuth requests to inherited vendor origins.
 * Explicitly supply a matching Flind endpoint and *registered* OAuth ID. */
export function configuredFlindHostedCloud(region: HostedRegion): CustomCloud {
  const names = ENV_KEYS[region];
  const cloud = normalizeCustomCloud({
    url: readPublicConfig(names.url),
    oauthClientId: readPublicConfig(names.oauthClientId),
  });
  if (!cloud) {
    throw new Error(
      "Flind " +
        region +
        " Cloud is not configured: set " +
        names.url +
        " and " +
        names.oauthClientId +
        " to independently controlled values",
    );
  }
  return cloud;
}
