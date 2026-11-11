import { useServiceOptional } from "@flind/di/react";
import { Switch } from "@flind/quill";
import { ANALYTICS_EVENTS } from "@flind/shared";
import {
  MISSION_CONTROL_CLIENT,
  type MissionControlClient,
} from "@flind/ui/features/mission-control/identifiers";
import {
  SettingsCard,
  SettingsCardRow,
} from "@flind/ui/features/settings/components/SettingsCard";
import { SettingsSegmented } from "@flind/ui/features/settings/components/SettingsSegmented";
import { ThemePicker } from "@flind/ui/features/settings/components/ThemePicker";
import {
  type NavRailSize,
  useSettingsStore,
} from "@flind/ui/features/settings/settingsStore";
import { track } from "@flind/ui/shell/analytics";
import type { ThemePreference } from "@flind/ui/shell/themeStore";
import { useThemeStore } from "@flind/ui/shell/themeStore";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

export function AppearanceSettings() {
  const theme = useThemeStore((state) => state.theme);
  const setTheme = useThemeStore((state) => state.setTheme);

  // Mission Control overlay state. The client is bound on desktop only, so on
  // other hosts this resolves to null and the setting is hidden.
  const queryClient = useQueryClient();
  const missionControl = useServiceOptional<MissionControlClient>(
    MISSION_CONTROL_CLIENT,
  );
  const { data: missionControlSupported } = useQuery({
    queryKey: ["missionControlOverlay", "supported"],
    queryFn: () => missionControl?.isSupported() ?? false,
    enabled: missionControl != null,
  });
  const { data: missionControlEnabled } = useQuery({
    queryKey: ["missionControlOverlay", "enabled"],
    queryFn: () => missionControl?.getEnabled() ?? false,
    enabled: missionControl != null && missionControlSupported === true,
  });
  const missionControlMutation = useMutation({
    mutationFn: (enabled: boolean) =>
      missionControl?.setEnabled(enabled) ?? Promise.resolve(),
  });

  const handleMissionControlOverlayChange = useCallback(
    (checked: boolean) => {
      track(ANALYTICS_EVENTS.SETTING_CHANGED, {
        setting_name: "mission_control_overlay",
        new_value: checked,
        old_value: !checked,
      });
      queryClient.setQueryData(["missionControlOverlay", "enabled"], checked);
      missionControlMutation.mutate(checked);
    },
    [missionControlMutation, queryClient],
  );

  const navRailSize = useSettingsStore((state) => state.navRailSize);
  const setNavRailSize = useSettingsStore((state) => state.setNavRailSize);
  const handleNavRailSizeChange = useCallback(
    (value: NavRailSize) => {
      track(ANALYTICS_EVENTS.SETTING_CHANGED, {
        setting_name: "nav_rail_size",
        new_value: value,
        old_value: navRailSize,
      });
      setNavRailSize(value);
    },
    [navRailSize, setNavRailSize],
  );

  const handleThemeChange = useCallback(
    (value: ThemePreference) => {
      track(ANALYTICS_EVENTS.SETTING_CHANGED, {
        setting_name: "theme",
        new_value: value,
        old_value: theme,
      });
      setTheme(value);
    },
    [theme, setTheme],
  );

  return (
    <div className="flex flex-col gap-3">
      <ThemePicker value={theme} onChange={handleThemeChange} />
      <SettingsCard>
        <SettingsCardRow
          label="Navigation rail"
          description="Size of the icons down the left edge. Small hides their labels."
        >
          <SettingsSegmented
            ariaLabel="Navigation rail size"
            value={navRailSize}
            options={[
              { value: "small", label: "Small" },
              { value: "medium", label: "Medium" },
              { value: "large", label: "Large" },
            ]}
            onValueChange={(value) =>
              handleNavRailSizeChange(value as NavRailSize)
            }
          />
        </SettingsCardRow>
      </SettingsCard>
      {missionControl != null && missionControlSupported === true && (
        <SettingsCard>
          <SettingsCardRow
            label="Mission Control overlay"
            description="Show the Flind logo over the window in macOS Mission Control"
          >
            <Switch
              size="sm"
              checked={missionControlEnabled ?? false}
              onCheckedChange={handleMissionControlOverlayChange}
            />
          </SettingsCardRow>
        </SettingsCard>
      )}
    </div>
  );
}
