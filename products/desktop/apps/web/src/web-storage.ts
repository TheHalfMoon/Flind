import { registerRendererStateStorage } from "@flind/ui/shell/rendererStorage";
import { rawLocalStorage } from "./web-local-store";

// Web persistence backend for @flind/ui stores (drafts, settings, layout).
// Desktop persists through the host; web uses origin-scoped localStorage via the
// shared seam (web-local-store).
registerRendererStateStorage(rawLocalStorage);
