import { DESKTOP_WORK_LAYOUT_FLAG } from "@flind/shared";
import { useChannelsLayout } from "@flind/ui/features/canvas/hooks/useChannelsLayout";
import { useFeatureFlag } from "@flind/ui/features/feature-flags/useFeatureFlag";

export function useWorkLayout(): boolean {
  const channelsLayout = useChannelsLayout();
  const enabled = useFeatureFlag(DESKTOP_WORK_LAYOUT_FLAG, import.meta.env.DEV);
  return channelsLayout && enabled;
}
