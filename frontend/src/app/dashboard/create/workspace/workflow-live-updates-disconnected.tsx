"use client";

/**
 * AE-0440: visible "live updates disconnected" state of the create workspace.
 *
 * Shown when the workflow stream gave up reconnecting (budget spent, workflow
 * gone): the page no longer pretends its state is live, and Retry reopens the
 * stream with a fresh attempt budget.
 */

import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import {
  NeonAlert,
  NeonAlertDescription,
  NeonAlertTitle,
} from "@/components/molecules/neon-alert";

interface WorkflowLiveUpdatesDisconnectedProps {
  onRetry: () => void;
}

export function WorkflowLiveUpdatesDisconnected({
  onRetry,
}: WorkflowLiveUpdatesDisconnectedProps): React.JSX.Element {
  const t = useTranslations("editorialWorkflow.transport");
  return (
    <NeonAlert role="status" data-testid="live-updates-disconnected">
      <NeonAlertTitle>{t("disconnectedTitle")}</NeonAlertTitle>
      <NeonAlertDescription>
        <p className="pb-1">{t("disconnectedHint")}</p>
        <NeonButton type="button" variant="outline" size="sm" onClick={onRetry}>
          {t("retry")}
        </NeonButton>
      </NeonAlertDescription>
    </NeonAlert>
  );
}
