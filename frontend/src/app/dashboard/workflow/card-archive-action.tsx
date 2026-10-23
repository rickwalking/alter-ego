"use client";

import { useId, useState } from "react";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { ARCHIVE_REFUSAL, WORKFLOW_API } from "@/constants/workflow";
import { NEON_RED, TEXT_DIM, TEXT_MUTED } from "@/constants/neon";
import { useWorkflowPostAction } from "@/modules/editorial";
import type { CardArchiveActionProps } from "./types";

const NO_MESSAGE = "";

/**
 * "Arquivar" (with a confirmation) on an active card, "Restaurar" on an
 * archived one. A published card has no control; a card whose phase is in
 * progress shows a disabled "Arquivar" with the reason. Only a failure is
 * shown: a success takes the card off this board.
 */
export function CardArchiveAction({
  card,
  archived,
  onChanged,
}: Readonly<CardArchiveActionProps>): React.ReactElement | null {
  const t = useTranslations("workflow.archive");
  const reasonId = useId();
  const [confirming, setConfirming] = useState(false);
  const archive = useWorkflowPostAction(
    { success: NO_MESSAGE, failed: t("archiveFailed") },
    onChanged,
  );
  const restore = useWorkflowPostAction(
    { success: NO_MESSAGE, failed: t("restoreFailed") },
    onChanged,
  );

  if (archived) {
    return (
      <div className="flex flex-wrap items-center gap-2 px-1">
        <NeonButton
          size="sm"
          variant="secondary"
          disabled={restore.submitting}
          onClick={() =>
            void restore.post(WORKFLOW_API.CAROUSEL_RESTORE(card.id), {})
          }
        >
          {t("restore")}
        </NeonButton>
        {restore.message && (
          <p role="alert" className="text-xs" style={{ color: NEON_RED }}>
            {restore.message}
          </p>
        )}
      </div>
    );
  }
  if (card.archiveRefusal === ARCHIVE_REFUSAL.PUBLISHED) return null;
  if (card.archiveRefusal === ARCHIVE_REFUSAL.IN_PROGRESS) {
    return (
      <div className="flex flex-wrap items-center gap-2 px-1">
        <NeonButton
          size="sm"
          variant="secondary"
          disabled
          aria-describedby={reasonId}
        >
          {t("archive")}
        </NeonButton>
        <p id={reasonId} className="text-[11px]" style={{ color: TEXT_DIM }}>
          {t("inProgress")}
        </p>
      </div>
    );
  }
  if (!confirming) {
    return (
      <div className="px-1">
        <NeonButton
          size="sm"
          variant="secondary"
          onClick={() => setConfirming(true)}
        >
          {t("archive")}
        </NeonButton>
      </div>
    );
  }
  return (
    <div className="space-y-1 px-1">
      <p className="text-xs" style={{ color: TEXT_MUTED }}>
        {t("confirm")}
      </p>
      <div className="flex flex-wrap gap-2">
        <NeonButton
          size="sm"
          variant="danger"
          disabled={archive.submitting}
          onClick={() =>
            void archive.post(WORKFLOW_API.CAROUSEL_ARCHIVE(card.id), {})
          }
        >
          {t("confirmYes")}
        </NeonButton>
        <NeonButton
          size="sm"
          variant="secondary"
          onClick={() => setConfirming(false)}
        >
          {t("cancel")}
        </NeonButton>
      </div>
      {archive.message && (
        <p role="alert" className="text-xs" style={{ color: NEON_RED }}>
          {archive.message}
        </p>
      )}
    </div>
  );
}
