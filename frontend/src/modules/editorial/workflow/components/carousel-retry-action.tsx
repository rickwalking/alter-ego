"use client";

import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { TEXT_MUTED } from "@/constants/neon";
import { RETRY_KINDS } from "@/constants/workflow";
import type { CarouselRetryActionProps } from "./types";

const REASON_ID = "workspace-retry-reason";

function isKnownKind(kind: string | null | undefined): kind is string {
  return typeof kind === "string" && RETRY_KINDS.has(kind);
}

/** Retry on the phase card, with what it runs or why it cannot run. */
export function CarouselRetryAction({
  capability,
  pending,
  canSubmit,
  error,
  onRetry,
}: Readonly<CarouselRetryActionProps>): React.ReactElement {
  const t = useTranslations("workflow.retry");
  const kind = capability?.retry_kind;
  let reason: string | null = isKnownKind(kind) ? t(`kind.${kind}`) : null;
  if (!canSubmit) reason = t("errors.unavailable");
  if (error) reason = error;
  if (pending) reason = null;
  return (
    <div className="space-y-1">
      <NeonButton
        size="sm"
        aria-describedby={reason ? REASON_ID : undefined}
        loading={pending}
        disabled={!canSubmit}
        onClick={onRetry}
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
