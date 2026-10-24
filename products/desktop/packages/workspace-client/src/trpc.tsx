import type { AppRouter } from "@flind/workspace-server/trpc";
import { createTRPCContext } from "@trpc/tanstack-react-query";

export const {
  TRPCProvider: WorkspaceTRPCProvider,
  useTRPC: useWorkspaceTRPC,
} = createTRPCContext<AppRouter>();
