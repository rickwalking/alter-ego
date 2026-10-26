"use client";

import { useEffect, useId, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { TEXT_MUTED } from "@/constants/neon";
import type { QueueRowActionProps } from "./types";

const ESCAPE_KEY = "Escape";

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
  const triggerRef = useRef<HTMLButtonElement>(null);
  const destructiveRef = useRef<HTMLButtonElement>(null);
  const restoreFocusRef = useRef(false);
  const accessibleName = t("actionForTheme", { action: label, theme });

  useEffect(() => {
    if (confirming) {
      destructiveRef.current?.focus();
      return;
    }
    if (!restoreFocusRef.current) return;
    restoreFocusRef.current = false;
    triggerRef.current?.focus();
  }, [confirming]);

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
  const cancelConfirmation = (): void => {
    restoreFocusRef.current = true;
    setConfirming(false);
  };
  const handleConfirmationKeyDown = (
    event: React.KeyboardEvent<HTMLDivElement>,
  ): void => {
    if (event.key !== ESCAPE_KEY) return;
    event.preventDefault();
    event.stopPropagation();
    cancelConfirmation();
  };

  if (confirmation !== undefined && confirming) {
    return (
      <div
        role="group"
        aria-labelledby={confirmationId}
        className="flex max-w-72 flex-col gap-1"
        onKeyDown={handleConfirmationKeyDown}
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
            ref={destructiveRef}
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
      ref={triggerRef}
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
