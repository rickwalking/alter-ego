"use client";

import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { TEXT_DIM } from "@/constants/neon";
import { SECTION_CARD_STYLE } from "@/modules/publishing/distribution/constants";
import type { SlideEditActionsProps, SlideEditStatusProps } from "./types";

export function RunInProgressCard(): React.ReactElement {
  const t = useTranslations("publish.slideEditor");
  return (
    <div style={SECTION_CARD_STYLE}>
      <h3 className="text-sm font-semibold mb-1">{t("title")}</h3>
      <p className="text-xs" style={{ color: TEXT_DIM }} role="status">
        {t("blockedRunInProgress")}
      </p>
    </div>
  );
}

/** Save (or "submit manual fixes" after a refused save) and cancel. */
export function SlideEditActions({
  refused,
  canSave,
  saving,
  onSave,
  onCancel,
}: SlideEditActionsProps): React.ReactElement {
  const t = useTranslations("publish.slideEditor");
  const tErrors = useTranslations("editorialWorkflow.review.fieldErrors");
  const savingLabel = refused ? tErrors("submittingManualFixes") : t("saving");
  const saveLabel = refused ? tErrors("submitManualFixes") : t("save");
  return (
    <div className="flex flex-wrap items-center gap-2">
      <NeonButton size="sm" disabled={!canSave || saving} onClick={onSave}>
        {saving ? savingLabel : saveLabel}
      </NeonButton>
      <NeonButton size="sm" variant="outline" onClick={onCancel}>
        {t("cancel")}
      </NeonButton>
    </div>
  );
}

/** The rebuild-pending note, then the success line once rebuilt. */
export function SlideEditStatus({
  pending,
  done,
}: SlideEditStatusProps): React.ReactElement | null {
  const t = useTranslations("publish.slideEditor");
  if (pending) {
    return (
      <p
        className="text-xs mt-2 text-[var(--color-warning,#b45309)]"
        role="status"
      >
        {t("rebuildPending")}
      </p>
    );
  }
  if (!done) {
    return null;
  }
  return (
    <p className="text-xs mt-2 text-success" role="status">
      {t("success")}
    </p>
  );
}
