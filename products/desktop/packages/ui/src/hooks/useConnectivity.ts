import { connectivityStore } from "@flind/core/connectivity/connectivityStore";
import { createSelectors } from "./createSelectors";

const connectivity = createSelectors(connectivityStore);

export function useConnectivity() {
  return { isOnline: connectivity.use.isOnline() };
}
