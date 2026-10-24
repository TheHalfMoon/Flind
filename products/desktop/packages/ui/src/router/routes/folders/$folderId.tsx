import { FolderSettingsView } from "@flind/ui/features/settings/FolderSettingsView";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/folders/$folderId")({
  component: FolderSettingsView,
});
