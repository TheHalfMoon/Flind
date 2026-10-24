import { SHELL_PROCESS_POLLER } from "@flind/core/terminal/identifiers";
import type { ShellProcessPoller } from "@flind/core/terminal/shellProcessPoller";
import { useService } from "@flind/di/react";
import { useTerminalStore } from "@flind/ui/features/terminal/terminalStore";
import { useEffect } from "react";

export function useShellProcessPoller(key: string): void {
  const poller = useService<ShellProcessPoller>(SHELL_PROCESS_POLLER);

  useEffect(() => {
    const sessionId =
      useTerminalStore.getState().terminalStates[key]?.sessionId;
    if (!sessionId) return;

    const setProcessName = useTerminalStore.getState().setProcessName;
    const initial =
      useTerminalStore.getState().terminalStates[key]?.processName ?? null;

    poller.start(
      key,
      sessionId,
      (processName) => setProcessName(key, processName),
      initial,
    );

    return () => poller.stop(key);
  }, [key, poller]);
}
