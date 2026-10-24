import type { SignalReport } from "@flind/shared/types";
import { createContext, useContext } from "react";

export const ReportPageContext = createContext<SignalReport | null>(null);

export function useReportPage() {
  return useContext(ReportPageContext);
}
