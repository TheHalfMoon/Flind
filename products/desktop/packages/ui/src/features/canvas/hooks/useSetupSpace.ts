import type {
  SpaceSetupInput,
  SpaceSetupStarted,
} from "@flind/shared/domain-types";
import { useOptionalAuthenticatedClient } from "@flind/ui/features/auth/authClient";
import { channelFeedQueryKey } from "@flind/ui/features/canvas/hooks/useChannelFeed";
import { channelFeedMessagesQueryKey } from "@flind/ui/features/canvas/hooks/useChannelFeedMessages";
import { useMutation, useQueryClient } from "@tanstack/react-query";

/**
 * Starts the server-built task that sets a space up for a goal or a feature.
 * The backend files the task into the channel and posts the feed row, so this
 * only has to refresh the feed the user lands on.
 */
export function useSetupSpace() {
  const client = useOptionalAuthenticatedClient();
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async (input: {
      channelId: string;
      setup: SpaceSetupInput;
    }): Promise<SpaceSetupStarted> => {
      if (!client) throw new Error("Not authenticated");
      return client.setupTaskChannel(input.channelId, input.setup);
    },
    onSuccess: (_result, input) => {
      void queryClient.invalidateQueries({
        queryKey: channelFeedQueryKey(input.channelId),
      });
      void queryClient.invalidateQueries({
        queryKey: channelFeedMessagesQueryKey(input.channelId),
      });
    },
  });

  return { setup: mutation.mutateAsync, isStarting: mutation.isPending };
}
