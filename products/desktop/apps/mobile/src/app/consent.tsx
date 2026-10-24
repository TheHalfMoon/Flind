import { Text } from "@components/text";
import { router } from "expo-router";
import { ActivityIndicator, Pressable, ScrollView, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useAuthStore, useUserQuery } from "@/features/auth";
import { ConsentError } from "@/features/consent/components/ConsentError";
import { ConsentPanel } from "@/features/consent/components/ConsentPanel";
import { useOrgConsent } from "@/features/consent/hooks/useOrgConsent";

import { useThemeColors } from "@/lib/theme";

const ORGANIZATION_ADMIN_LEVEL = 8;

export default function ConsentScreen() {
  const themeColors = useThemeColors();
  const consent = useOrgConsent();
  const { data: user } = useUserQuery();
  const logout = useAuthStore((s) => s.logout);
  const organization = user?.organization;
  const isAdmin =
    (organization?.membership_level ?? 0) >= ORGANIZATION_ADMIN_LEVEL;

  const handleLogout = async (): Promise<void> => {
    await logout();
    router.replace("/auth");
  };

  return (
    <SafeAreaView className="flex-1 bg-gray-1">
      <ScrollView
        className="flex-1"
        contentContainerClassName="px-6 pt-12 pb-8"
        keyboardShouldPersistTaps="handled"
      >
        {consent.status === "error" ? (
          <ConsentError onRetry={consent.retry} />
        ) : consent.status === "resolved" && !consent.satisfied ? (
          <ConsentPanel
            organizationName={organization?.name}
            needsAiConsent={consent.needsAiConsent}
            needsBetaTerms={consent.needsBetaTerms}
            isAdmin={isAdmin}
          />
        ) : (
          <View className="items-center py-24">
            <ActivityIndicator size="large" color={themeColors.accent[9]} />
          </View>
        )}
      </ScrollView>
      <View className="flex-row items-center justify-between px-6 pb-4">
        <Text className="text-gray-11 text-sm">
          Support link not configured
        </Text>
        <Pressable onPress={handleLogout}>
          <Text className="text-gray-11 text-sm">Log out</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}
