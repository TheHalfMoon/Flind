import { useOptionalAuthenticatedClient } from "@flind/ui/features/auth/authClient";
import { useAuthStateValue } from "@flind/ui/features/auth/store";
import { useCurrentUser } from "@flind/ui/features/auth/useCurrentUser";

export function useServerArchiveScope(): string | null {
  const client = useOptionalAuthenticatedClient();
  const authState = useAuthStateValue((state) => state);
  const { data: currentUser } = useCurrentUser({ client });

  if (
    !currentUser ||
    !authState.cloudRegion ||
    authState.currentProjectId === null
  ) {
    return null;
  }

  return JSON.stringify([
    authState.cloudRegion,
    currentUser.uuid,
    authState.currentProjectId,
  ]);
}
