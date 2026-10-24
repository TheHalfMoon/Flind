import type {
  SpeechSettingsProvider,
  UserNameProvider,
} from "@flind/core/speech/identifiers";
import type { ISpeech } from "@flind/platform/speech";
import { authKeys } from "@flind/ui/features/auth/useCurrentUser";
import type { ISpeechNotifySettings } from "@flind/ui/features/notifications/identifiers";
import {
  notificationsPaused,
  useSettingsStore,
} from "@flind/ui/features/settings/settingsStore";
import type { ImperativeQueryClient } from "@flind/ui/shell/queryClient";
import {
  isSpeechSupported,
  speakSystemVoice,
  stopSpeech,
} from "@flind/ui/utils/speech";

// System voice only: ElevenLabs synthesis needs the key in a host secure store,
// which the browser has no equivalent of. voiceId is therefore ignored.
export const webSpeech: ISpeech = {
  isSupported: () => isSpeechSupported(),
  speak: (text) => speakSystemVoice(text),
  stop: () => stopSpeech(),
};

export const webSpeechSettings: SpeechSettingsProvider = {
  get: () => ({ enabled: useSettingsStore.getState().spokenNotifications }),
};

export const webSpeechNotifySettings: ISpeechNotifySettings = {
  get: () => {
    const s = useSettingsStore.getState();
    return {
      enabled:
        s.spokenNotifications &&
        !notificationsPaused(s.notificationsPausedUntil),
      needsInput: s.spokenNotifyNeedsInput,
      completion: s.spokenNotifyCompletion,
      progress: s.spokenNotifyProgress,
      focusMode: s.spokenFocusMode,
    };
  },
};

export function createWebSpeechUserName(
  queryClient: ImperativeQueryClient,
): UserNameProvider {
  return {
    getFirstName: () => {
      for (const [, data] of queryClient.getQueriesData({
        queryKey: authKeys.currentUsers(),
      })) {
        const first = (
          data as { first_name?: string | null } | undefined
        )?.first_name?.trim();
        if (first) return first;
      }
      return undefined;
    },
  };
}
