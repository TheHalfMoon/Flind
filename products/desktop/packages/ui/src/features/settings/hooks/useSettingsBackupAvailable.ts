import { useServiceOptional } from "@flind/di/react";
import { SETTINGS_BACKUP_FILES } from "@flind/platform/settings-backup-files";
import { SETTINGS_BACKUP_FLAG } from "@flind/shared";
import { useFeatureFlag } from "@flind/ui/features/feature-flags/useFeatureFlag";

export function useSettingsBackupAvailable(): boolean {
  const files = useServiceOptional(SETTINGS_BACKUP_FILES);
  const enabled = useFeatureFlag(SETTINGS_BACKUP_FLAG);
  return files !== null && enabled;
}
