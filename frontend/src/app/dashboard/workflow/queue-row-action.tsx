"use client";

import { useId, useState } from "react";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { TEXT_MUTED } from "@/constants/neon";
import type { QueueRowActionProps } from "./types";

/** One theme-named row action, with an optional inline destructive confirmation. */
export function QueueRowAction({
  id,
  action,
  theme,
  label,
  pending,
  onAction,
  disabled = false,
  variant = "secondary",
  confirmation,
  pendingLabel,
  describedBy,
  reprocess,
}: Readonly<QueueRowActionProps>): React.ReactElement {
  const t = useTranslations("workflow.queue");
  const [confirming, setConfirming] = useState(false);
  const confirmationId = useId();
  const accessibleName = t("actionForTheme", { action: label, theme });

  const commitAction = (): void => {
    setConfirming(false);
    if (reprocess !== undefined) {
      onAction(action, id, reprocess);
      return;
    }
    onAction(action, id);
  };
  const startAction = (): void => {
    if (confirmation !== undefined) {
      setConfirming(true);
      return;
    }
    commitAction();
  };
  const cancelConfirmation = (): void => setConfirming(false);

  if (confirmation !== undefined && confirming) {
    return (
      <div
        role="group"
        aria-labelledby={confirmationId}
        className="flex max-w-72 flex-col gap-1"
      >
        <p
          id={confirmationId}
          className="text-xs"
          style={{ color: TEXT_MUTED }}
        >
          {confirmation}
        </p>
        <div className="flex flex-wrap gap-2">
          <NeonButton
            size="sm"
            variant="danger"
            aria-label={accessibleName}
            disabled={pending}
            onClick={commitAction}
          >
            {label}
          </NeonButton>
          <NeonButton
            size="sm"
            variant="secondary"
            aria-label={t("actionForTheme", {
              action: t("confirmBack"),
              theme,
            })}
            onClick={cancelConfirmation}
          >
            {t("confirmBack")}
          </NeonButton>
        </div>
      </div>
    );
  }

  return (
    <NeonButton
      size="sm"
      variant={variant}
      aria-label={accessibleName}
      aria-describedby={describedBy}
      loading={pending}
      disabled={disabled}
      onClick={startAction}
    >
      {pending && pendingLabel !== undefined ? pendingLabel : label}
    </NeonButton>
  );
}
