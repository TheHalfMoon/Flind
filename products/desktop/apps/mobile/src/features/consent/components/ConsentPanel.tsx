import { Text } from "@components/text";
import { View } from "react-native";

interface ConsentPanelProps {
  organizationName?: string;
  needsAiConsent: boolean;
  needsBetaTerms: boolean;
  isAdmin: boolean;
}

/** Flind does not yet have reviewed first-party data processing disclosures
 * or beta terms. Do not collect approval for a different vendor's terms. */
export function ConsentPanel({
  organizationName,
  needsAiConsent,
  needsBetaTerms,
  isAdmin,
}: ConsentPanelProps) {
  return (
    <View className="gap-5">
      <View className="gap-1">
        <Text className="font-semibold text-2xl text-gray-12">
          Flind consent review required
        </Text>
        <Text className="text-base text-gray-11">
          {organizationName
            ? organizationName +
              " cannot proceed until Flind disclosures and terms have been reviewed for this deployment."
            : "This organization cannot proceed until Flind disclosures and terms have been reviewed for this deployment."}
        </Text>
      </View>
      {needsAiConsent && (
        <View className="gap-2 rounded-lg border border-gray-6 bg-gray-2 p-4">
          <Text className="font-semibold text-base text-gray-12">
            AI data-processing approval unavailable
          </Text>
          <Text className="text-gray-11 text-sm leading-5">
            Data recipients, processing purposes, retention terms, and the
            applicable policy must be verified for this Flind installation
            before any AI approval can be requested.
          </Text>
        </View>
      )}
      {needsBetaTerms && (
        <View className="gap-2 rounded-lg border border-gray-6 bg-gray-2 p-4">
          <Text className="font-semibold text-base text-gray-12">
            Flind beta terms unavailable
          </Text>
          <Text className="text-gray-11 text-sm leading-5">
            The inherited provider's beta terms do not constitute Flind terms.
            No beta acceptance can be submitted until reviewed terms and
            first-party consent are configured.
          </Text>
        </View>
      )}
      <Text className="text-gray-11 text-sm leading-5">
        {isAdmin
          ? "An organization administrator must arrange a review of the terms and data-processing disclosures before onboarding can be enabled."
          : "Contact an organization administrator about the missing Flind terms and data-processing disclosures."}
      </Text>
    </View>
  );
}
