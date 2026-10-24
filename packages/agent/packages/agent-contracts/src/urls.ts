import { getCustomCloud } from "./custom-cloud";
import { configuredFlindHostedCloud } from "./flind-hosted-cloud";
import type { CloudRegion } from "./regions";

export function getCloudUrlFromRegion(region: CloudRegion): string {
  switch (region) {
    case "us":
    case "eu":
    case "dev-cloud":
      return configuredFlindHostedCloud(region).url;
    case "dev":
      return "http://localhost:8010";
    case "custom": {
      const cloud = getCustomCloud();
      if (!cloud) throw new Error("Flind custom Cloud is not configured");
      return cloud.url;
    }
  }
}
