"use client";

import { useTranslations } from "next-intl";
import { ARCHIVE_REFUSAL } from "@/constants/workflow";
import { TEXT_DIM } from "@/constants/neon";
import { useWorkflowPostAction } from "@/modules/editorial";
import { CardArchiveMenuItems } from "./card-archive-menu-items";
import { useCardOverflowMenu } from "./use-card-overflow-menu";
import type { CardArchiveActionProps } from "./types";

const NO_MESSAGE = "";

const OUTLINE_FOCUS_CLASS =
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-neon-cyan";

const TRIGGER_CLASS = `absolute top-1 right-1 z-10 flex h-7 w-7 items-center justify-center rounded-md border border-[var(--color-neon-border-subtle)] bg-bg-deep text-sm leading-none transition-colors hover:border-neon-cyan/60 hover:text-white ${OUTLINE_FOCUS_CLASS}`;

const MENU_CLASS = `fixed z-50 min-w-[160px] rounded-md border border-[var(--color-neon-border-subtle)] bg-bg-deep p-1 shadow-[var(--shadow-neon-button)] ${OUTLINE_FOCUS_CLASS}`;

const MENU_WIDTH_PX = 224;

/**
 * The per-card overflow menu holding "Arquivar" (with the confirmation) or
 * "Restaurar", or the refusal reason as disabled text. Fixed-positioned so
 * the column scroll container cannot clip it; Escape closes it and returns
 * focus to the trigger. On the board, only the roving card's trigger stays
 * in the tab order (`tabbable`).
 */
export function CardArchiveAction({
  card,
  archived,
  onChanged,
  tabbable = true,
}: Readonly<CardArchiveActionProps>): React.ReactElement | null {
  const t = useTranslations("workflow.archive");
  const {
    open,
    confirming,
    onConfirmingChange,
    triggerRef,
    menuRef,
    position,
    openMenu,
    closeMenu,
    onMenuKeyDown,
    onMenuBlur,
  } = useCardOverflowMenu();
  const archive = useWorkflowPostAction(
    { success: NO_MESSAGE, failed: t("archiveFailed") },
    onChanged,
  );
  const restore = useWorkflowPostAction(
    { success: NO_MESSAGE, failed: t("restoreFailed") },
    onChanged,
  );

  if (!card.canArchive) return null;
  if (!archived && card.archiveRefusal === ARCHIVE_REFUSAL.PUBLISHED) {
    return null;
  }

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        aria-label={t("menuLabel", { title: card.title })}
        aria-haspopup="menu"
        aria-expanded={open}
        tabIndex={tabbable ? 0 : -1}
        onClick={() => (open ? closeMenu(true) : openMenu())}
        className={TRIGGER_CLASS}
        style={{ color: TEXT_DIM }}
      >
        ⋯
      </button>
      {open && (
        <div
          ref={menuRef}
          role="menu"
          aria-label={t("menuLabel", { title: card.title })}
          tabIndex={-1}
          onKeyDown={onMenuKeyDown}
          onBlur={onMenuBlur}
          className={MENU_CLASS}
          style={{
            top: position.top,
            left: position.left,
            width: MENU_WIDTH_PX,
          }}
        >
          <CardArchiveMenuItems
            card={card}
            archived={archived}
            confirming={confirming}
            onConfirmingChange={onConfirmingChange}
            archive={archive}
            restore={restore}
          />
        </div>
      )}
    </>
  );
}
