"use client";

import { NeonConfirmDialog } from "@/components/molecules/neon-confirm-dialog";

/** The API answers 409 when other records still reference the item. */
const HTTP_CONFLICT = 409;

export interface NeonDeleteConfirmProps {
  /**
   * The page's `<entity>.delete` translator: `title`, `body` (with `{name}`),
   * `confirm`, `cancel`, `error` and `inUse`.
   */
  t: (key: string, values?: Record<string, string>) => string;
  name: string;
  onConfirm: () => Promise<void>;
  onClose: () => void;
}

/** Asks before deleting a named item; a 409 says it is still in use. */
export function NeonDeleteConfirm({
  t,
  name,
  onConfirm,
  onClose,
}: Readonly<NeonDeleteConfirmProps>): React.ReactElement {
  return (
    <NeonConfirmDialog
      title={t("title")}
      body={t("body", { name })}
      confirmLabel={t("confirm")}
      cancelLabel={t("cancel")}
      errorFallback={t("error")}
      statusMessages={{ [HTTP_CONFLICT]: t("inUse") }}
      onConfirm={onConfirm}
      onClose={onClose}
    />
  );
}
