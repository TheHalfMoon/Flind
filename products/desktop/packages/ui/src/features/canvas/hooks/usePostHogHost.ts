import { getCloudUrlFromRegion } from "@flind/shared";
import { useAuthStateValue } from "@flind/ui/features/auth/store";

export function usePostHogHost(): string | null {
  const cloudRegion = useAuthStateValue((state) => state.cloudRegion);
  try {
    return cloudRegion
      ? new URL(getCloudUrlFromRegion(cloudRegion)).host
      : null;
  } catch {
    return null;
  }
}
