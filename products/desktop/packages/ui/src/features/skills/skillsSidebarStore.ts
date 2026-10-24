import { createSidebarStore } from "@flind/ui/shell/createSidebarStore";

export const useSkillsSidebarStore = createSidebarStore({
  name: "skills-sidebar",
  defaultWidth: 380,
});
