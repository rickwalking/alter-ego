"use client";

import { useTranslations } from "next-intl";
import { ARCHIVE_REFUSAL, WORKFLOW_API } from "@/constants/workflow";
import { NEON_RED, TEXT, TEXT_DIM } from "@/constants/neon";
import type { CardArchiveMenuItemsProps } from "./types";

const MENU_ITEM_CLASS =
  "block w-full rounded px-3 py-2 text-left text-sm transition-colors hover:bg-neon-cyan-dim focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-bg-deep disabled:cursor-not-allowed disabled:opacity-60";

const MENU_ITEM_DISABLED_CLASS = `${MENU_ITEM_CLASS} text-xs`;

const MENU_ITEM_DANGER_CLASS = `${MENU_ITEM_CLASS} font-semibold`;
const MENU_ITEM_SECONDARY_CLASS = `${MENU_ITEM_CLASS} text-white/80`;

const REFUSAL_REASON = {
  [ARCHIVE_REFUSAL.IN_PROGRESS]: "inProgress",
  [ARCHIVE_REFUSAL.AUTOPILOT]: "autopilot",
} as const;

/**
 * The content of a card's overflow menu: "Restaurar" on the archived board,
 * the refusal reason as disabled text, or "Arquivar" with the confirmation
 * step. Failures are announced with role="alert" inside the menu.
 */
export function CardArchiveMenuItems({
  card,
  archived,
  confirming,
  onConfirmingChange,
  archive,
  restore,
  reasonId,
}: Readonly<CardArchiveMenuItemsProps>): React.ReactElement {
  const t = useTranslations("workflow.archive");

  if (archived) {
    return (
      <div>
        <button
          type="button"
          role="menuitem"
          className={MENU_ITEM_CLASS}
          disabled={restore.submitting}
          onClick={() =>
            void restore.post(WORKFLOW_API.CAROUSEL_RESTORE(card.id), {})
          }
        >
          {t("restore")}
        </button>
        {restore.message && (
          <p
            role="alert"
            className="px-3 pt-1 text-xs"
            style={{ color: NEON_RED }}
          >
            {restore.message}
          </p>
        )}
      </div>
    );
  }
  if (
    card.archiveRefusal &&
    card.archiveRefusal !== ARCHIVE_REFUSAL.PUBLISHED
  ) {
    return (
      <button
        type="button"
        role="menuitem"
        disabled
        aria-describedby={reasonId}
        className={MENU_ITEM_DISABLED_CLASS}
        style={{ color: TEXT_DIM }}
      >
        {t(REFUSAL_REASON[card.archiveRefusal])}
      </button>
    );
  }
  if (!confirming) {
    return (
      <button
        type="button"
        role="menuitem"
        className={MENU_ITEM_CLASS}
        onClick={() => onConfirmingChange(true)}
      >
        {t("archive")}
      </button>
    );
  }
  return (
    <div className="space-y-1 p-1">
      <p className="px-2 text-xs" style={{ color: TEXT }}>
        {t("confirm")}
      </p>
      <button
        type="button"
        role="menuitem"
        className={MENU_ITEM_DANGER_CLASS}
        style={{ color: NEON_RED }}
        disabled={archive.submitting}
        onClick={() =>
          void archive.post(WORKFLOW_API.CAROUSEL_ARCHIVE(card.id), {})
        }
      >
        {t("confirmYes")}
      </button>
      <button
        type="button"
        role="menuitem"
        className={MENU_ITEM_SECONDARY_CLASS}
        onClick={() => onConfirmingChange(false)}
      >
        {t("cancel")}
      </button>
      {archive.message && (
        <p
          role="alert"
          className="px-2 pt-1 text-xs"
          style={{ color: NEON_RED }}
        >
          {archive.message}
        </p>
      )}
    </div>
  );
}
