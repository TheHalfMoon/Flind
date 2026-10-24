import {
  classifyIntegrations,
  type Integration,
} from "@flind/core/integrations/selectors";
import { create } from "zustand";

export type { Integration } from "@flind/core/integrations/selectors";

interface IntegrationStore {
  integrations: Integration[];
  setIntegrations: (integrations: Integration[]) => void;
}

export const useIntegrationStore = create<IntegrationStore>((set) => ({
  integrations: [],
  setIntegrations: (integrations) => set({ integrations }),
}));

export const useIntegrationSelectors = () => {
  const integrations = useIntegrationStore((state) => state.integrations);
  return classifyIntegrations(integrations);
};
