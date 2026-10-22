"use client";

import { useTranslations } from "next-intl";
import { NeonConfirmDialog } from "@/components/molecules/neon-confirm-dialog";
import type { LeaveGuardDialogProps } from "./types";

/** The page's own "discard unsaved edits?" dialog (no native confirm). */
export function LeaveGuardDialog({
  guard,
}: Readonly<LeaveGuardDialogProps>): React.ReactElement | null {
  const t = useTranslations("publish");
  if (!guard.asking) {
    return null;
  }
  return (
    <NeonConfirmDialog
      title={t("copy.leave.title")}
      body={t("copy.leave.body")}
      confirmLabel={t("copy.leave.confirm")}
      cancelLabel={t("copy.leave.cancel")}
      errorFallback={t("copy.errors.save")}
      onConfirm={guard.leave}
      onClose={guard.stay}
    />
  );
}
