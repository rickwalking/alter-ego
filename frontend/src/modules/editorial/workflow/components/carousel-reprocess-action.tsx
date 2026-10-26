"use client";

import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { TEXT_MUTED } from "@/constants/neon";
import { REPROCESS_REFUSAL_CODES } from "@/constants/workflow";
import type { CarouselReprocessActionProps } from "./types";

const REASON_ID = "workspace-reprocess-reason";

function isKnownRefusal(code: string | null): code is string {
  return code !== null && REPROCESS_REFUSAL_CODES.has(code);
}

export function CarouselReprocessAction({
  capability,
  pending,
  canSubmit,
  onReprocess,
}: Readonly<CarouselReprocessActionProps>): React.ReactElement {
  const t = useTranslations("workflow.reprocess");
  const code = capability.refusal_code;
  let refusal: string | null = null;
  if (isKnownRefusal(code)) refusal = t(`refusals.${code}`);
  let reason: string | null = null;
  if (pending) reason = t("pendingReason");
  if (!pending && !canSubmit) {
    reason = capability.can_reprocess
      ? t("errors.unavailable")
      : (refusal ?? t("refusals.unsupported"));
  }
  return (
    <div className="space-y-1">
      <NeonButton
        size="sm"
        variant="secondary"
        aria-label={t("action")}
        aria-describedby={reason ? REASON_ID : undefined}
        loading={pending}
        disabled={!canSubmit}
        onClick={onReprocess}
      >
        {pending ? t("pending") : t("action")}
      </NeonButton>
      {reason && (
        <p id={REASON_ID} className="text-xs" style={{ color: TEXT_MUTED }}>
          {reason}
        </p>
      )}
    </div>
  );
}
