import { ArrowClockwise } from "@phosphor-icons/react";
import { Button, Text } from "@flind/quill";
import { useState } from "react";
import type { OrgConsent } from "./useOrgConsent";

interface ConsentPanelProps {
  consent: Extract<OrgConsent, { status: "resolved" }>;
  requirements?: {
    needsAiConsent: boolean;
    needsBetaTerms: boolean;
  };
  isAdmin: boolean;
}

/**
 * Read-only legal qualification gate. Historical backend consent flags are
 * compatibility state, NOT authorization to accept another provider's policy.
 */
export function ConsentPanel({
  consent,
  requirements,
  isAdmin,
}: ConsentPanelProps) {
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const needsAiConsent = requirements?.needsAiConsent ?? consent.needsAiConsent;
  const needsBetaTerms = requirements?.needsBetaTerms ?? consent.needsBetaTerms;

  const refresh = async (): Promise<void> => {
    if (refreshing) return;
    setRefreshing(true);
    setError(null);
    try {
      await consent.retry();
    } catch {
      setError("Could not refresh Flind consent status. Try again.");
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="flex w-full max-w-[560px] flex-col gap-5">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="font-bold text-2xl text-foreground">
            Flind consent review required
          </h1>
          <Text size="sm" variant="muted">
            This organization cannot proceed until Flind policies and data
            processing disclosures are independently reviewed.
          </Text>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="shrink-0"
          loading={refreshing}
          data-attr="consent-refresh"
          onClick={() => void refresh()}
        >
          <ArrowClockwise />
          Refresh
        </Button>
      </header>

      {needsAiConsent && (
        <section className="rounded-lg border border-border bg-surface-primary px-4 py-4">
          <h2 className="font-semibold text-base text-foreground">
            AI data-processing approval unavailable
          </h2>
          <Text size="sm" variant="muted" className="mt-2">
            Flind must verify data recipients, purposes, storage and retention
            before requesting approval. The inherited provider's AI terms are
            not Flind terms.
          </Text>
        </section>
      )}

      {needsBetaTerms && (
        <section className="rounded-lg border border-border bg-surface-primary px-4 py-4">
          <h2 className="font-semibold text-base text-foreground">
            Flind beta terms unavailable
          </h2>
          <Text size="sm" variant="muted" className="mt-2">
            No beta acceptance can be submitted until independent Flind terms,
            subcontractor disclosures and consent storage are approved.
          </Text>
        </section>
      )}

      <Text size="sm" variant="muted">
        {isAdmin
          ? "An organization administrator must arrange first-party legal and data-processing review before onboarding can be enabled."
          : "Contact an organization administrator for first-party Flind terms and data-processing disclosures."}
      </Text>

      {error && (
        <div
          role="alert"
          className="rounded-lg border border-destructive/40 p-3 text-destructive-foreground"
        >
          {error}
        </div>
      )}
    </div>
  );
}
