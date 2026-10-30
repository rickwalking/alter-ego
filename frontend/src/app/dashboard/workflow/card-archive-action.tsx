"use client";

import { useEffect, useId, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { useTranslations } from "next-intl";
import { ARCHIVE_REFUSAL } from "@/constants/workflow";
import { TEXT_DIM } from "@/constants/neon";
import { useWorkflowPostAction } from "@/modules/editorial";
import { CardArchiveMenuItems } from "./card-archive-menu-items";
import type { CardArchiveActionProps } from "./types";

const NO_MESSAGE = "";
const MENU_WIDTH_PX = 224;
const MENU_GAP_PX = 4;
const MENU_EDGE_MARGIN_PX = 8;

const TRIGGER_CLASS =
  "absolute -top-2 -right-2 z-10 flex h-7 w-7 items-center justify-center rounded-md border border-[var(--color-neon-border-subtle)] bg-bg-deep text-sm leading-none transition-colors hover:border-neon-cyan/60 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-bg-deep";

const MENU_CLASS =
  "fixed z-50 min-w-[160px] rounded-md border border-[var(--color-neon-border-subtle)] bg-bg-deep p-1 shadow-[var(--shadow-neon-button)] focus-visible:outline-none";

interface MenuPosition {
  readonly top: number;
  readonly left: number;
}

function menuPosition(trigger: DOMRect): MenuPosition {
  const left = Math.max(
    MENU_EDGE_MARGIN_PX,
    Math.min(
      trigger.right - MENU_WIDTH_PX,
      window.innerWidth - MENU_WIDTH_PX - MENU_EDGE_MARGIN_PX,
    ),
  );
  return {
    top: trigger.bottom + MENU_GAP_PX,
    left,
  };
}

/**
 * The per-card overflow menu holding "Arquivar" (with the confirmation) or
 * "Restaurar", or the refusal reason as disabled text. Fixed-positioned so
 * the column scroll container cannot clip it; Escape closes it and returns
 * focus to the trigger.
 */
export function CardArchiveAction({
  card,
  archived,
  onChanged,
}: Readonly<CardArchiveActionProps>): React.ReactElement | null {
  const t = useTranslations("workflow.archive");
  const reasonId = useId();
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const [open, setOpen] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [position, setPosition] = useState<MenuPosition>({
    top: 0,
    left: 0,
  });
  const archive = useWorkflowPostAction(
    { success: NO_MESSAGE, failed: t("archiveFailed") },
    onChanged,
  );
  const restore = useWorkflowPostAction(
    { success: NO_MESSAGE, failed: t("restoreFailed") },
    onChanged,
  );

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: MouseEvent): void => {
      const target = event.target;
      if (!(target instanceof Node)) return;
      if (menuRef.current?.contains(target) === true) return;
      if (triggerRef.current?.contains(target) === true) return;
      setOpen(false);
      setConfirming(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [open]);

  useEffect(() => {
    if (open) menuRef.current?.focus();
  }, [open]);

  if (!card.canArchive) return null;
  if (!archived && card.archiveRefusal === ARCHIVE_REFUSAL.PUBLISHED) {
    return null;
  }

  function closeMenu(returnFocus: boolean): void {
    setOpen(false);
    setConfirming(false);
    if (returnFocus) triggerRef.current?.focus();
  }

  function openMenu(): void {
    const trigger = triggerRef.current?.getBoundingClientRect();
    if (trigger !== undefined) setPosition(menuPosition(trigger));
    setOpen(true);
  }

  function onMenuKeyDown(event: KeyboardEvent<HTMLDivElement>): void {
    if (event.key === "Escape") {
      event.preventDefault();
      closeMenu(true);
    }
  }

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        aria-label={t("menuLabel", { title: card.title })}
        aria-haspopup="menu"
        aria-expanded={open}
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
            onConfirmingChange={setConfirming}
            archive={archive}
            restore={restore}
            reasonId={reasonId}
          />
        </div>
      )}
    </>
  );
}
