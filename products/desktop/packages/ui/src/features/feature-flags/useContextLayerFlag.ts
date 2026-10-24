import { CONTEXT_LAYER_FLAG } from "@flind/shared";
import { useFeatureFlag } from "@flind/ui/features/feature-flags/useFeatureFlag";

export function useContextLayerFlag(): boolean {
  return useFeatureFlag(CONTEXT_LAYER_FLAG);
}
