import { leanSkillById } from "@flind/core/billing/leanSkills";
import { ANALYTICS_EVENTS, formatModelId } from "@flind/shared";
import { CostManagementView } from "@flind/ui/features/cost-management/CostManagementView";
import { CustomImageBuildDialog } from "@flind/ui/features/cost-management/CustomImageBuildDialog";
import { LeanSkillDialog } from "@flind/ui/features/cost-management/LeanSkillDialog";
import {
  useCostChecklist,
  useInstalledLeanSkills,
} from "@flind/ui/features/cost-management/useCostChecklist";
import { openSettings } from "@flind/ui/features/settings/hooks/useOpenSettings";
import { useSettingsStore } from "@flind/ui/features/settings/settingsStore";
import { skillErrorDescription } from "@flind/ui/features/skills/skillErrors";
import { useInstallMarketplaceSkill } from "@flind/ui/features/skills/useMarketplace";
import { useDeleteSkill } from "@flind/ui/features/skills/useSkillMutations";
import { toast } from "@flind/ui/primitives/toast";
import { track } from "@flind/ui/shell/analytics";
import { useState } from "react";

export function CostManagementSettings() {
  const setLastUsedModel = useSettingsStore((state) => state.setLastUsedModel);
  const setSte100Enabled = useSettingsStore((state) => state.setSte100Enabled);
  const markDone = useSettingsStore((state) => state.markCostChecklistDone);
  const items = useCostChecklist();
  const cloudRepository = useSettingsStore(
    (state) => state.lastUsedCloudRepository,
  );
  const installedSkills = useInstalledLeanSkills();
  const installSkill = useInstallMarketplaceSkill();
  const deleteSkill = useDeleteSkill();
  const [openSkillId, setOpenSkillId] = useState<string | null>(null);
  const [buildingImage, setBuildingImage] = useState(false);
  // A set, not one slot, so overlapping installs each disable and re-enable
  // only their own row instead of clobbering each other's busy state.
  const [busySkillIds, setBusySkillIds] = useState<ReadonlySet<string>>(
    new Set(),
  );
  const markSkillBusy = (skillId: string) =>
    setBusySkillIds((prev) => new Set(prev).add(skillId));
  const clearSkillBusy = (skillId: string) =>
    setBusySkillIds((prev) => {
      const next = new Set(prev);
      next.delete(skillId);
      return next;
    });
  const openSkill = openSkillId === null ? null : leanSkillById(openSkillId);
  const switchDefaultModel = (toModelId: string) => {
    const previous = useSettingsStore.getState().lastUsedModel;
    setLastUsedModel(toModelId);
    markDone("model-notch");
    toast.success(`New sessions start on ${formatModelId(toModelId)}`, {
      description: "Sessions already open keep the model they are on.",
      action: previous
        ? {
            label: "Undo",
            onClick: () => setLastUsedModel(previous),
          }
        : undefined,
    });
  };

  const toggleSte100 = (enabled: boolean) => {
    setSte100Enabled(enabled);
    track(ANALYTICS_EVENTS.SETTING_CHANGED, {
      setting_name: "simplified_technical_english",
      new_value: enabled,
    });
  };

  const installById = async (skillId: string) => {
    const skill = leanSkillById(skillId);
    if (!skill) return;
    markSkillBusy(skillId);
    try {
      await installSkill.mutateAsync({
        source: skill.source,
        ref: skill.ref,
        skillId: skill.skillId,
      });
      toast.success(`${skill.name} installed`, {
        description: "New sessions pick it up. Manage it under Skills.",
        action: { label: "Open skills", onClick: () => openSettings("skills") },
      });
    } catch (error) {
      toast.error(`Couldn't install ${skill.name}`, {
        description: skillErrorDescription(error),
      });
    } finally {
      clearSkillBusy(skillId);
    }
  };

  const uninstallById = async (skillId: string) => {
    const skill = leanSkillById(skillId);
    const skillPath = installedSkills.get(skillId);
    if (!skill || !skillPath) return;
    markSkillBusy(skillId);
    try {
      await deleteSkill.mutateAsync({ skillPath });
      toast.success(`${skill.name} uninstalled`, {
        description: "New sessions start without it.",
      });
    } catch (error) {
      toast.error(`Couldn't uninstall ${skill.name}`, {
        description: skillErrorDescription(error),
      });
    } finally {
      clearSkillBusy(skillId);
    }
  };

  return (
    <>
      <CostManagementView
        items={items}
        onSwitchModel={switchDefaultModel}
        onCreateImage={() => setBuildingImage(true)}
        onSte100Toggle={toggleSte100}
        onInstallSkill={(skillId) => void installById(skillId)}
        onUninstallSkill={(skillId) => void uninstallById(skillId)}
        onOpenSkill={setOpenSkillId}
        busySkillIds={busySkillIds}
      />
      {buildingImage && (
        <CustomImageBuildDialog
          defaultRepository={cloudRepository}
          onClose={() => setBuildingImage(false)}
        />
      )}
      {openSkill && (
        <LeanSkillDialog
          skill={openSkill}
          installed={installedSkills.has(openSkill.skillId)}
          busy={busySkillIds.has(openSkill.skillId)}
          onInstall={() => void installById(openSkill.skillId)}
          onUninstall={() => void uninstallById(openSkill.skillId)}
          onClose={() => setOpenSkillId(null)}
        />
      )}
    </>
  );
}
