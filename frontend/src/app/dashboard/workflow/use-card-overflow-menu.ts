"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { FocusEvent, KeyboardEvent, RefObject } from "react";
import type {
  CardOverflowMenu,
  MenuDismissalRefs,
  MenuPosition,
} from "./types";

const MENU_WIDTH_PX = 224;
const MENU_GAP_PX = 4;
const MENU_EDGE_MARGIN_PX = 8;

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

function enabledMenuItems(menu: HTMLElement | null): HTMLElement[] {
  if (menu === null) return [];
  return Array.from(
    menu.querySelectorAll<HTMLElement>(
      'button[role="menuitem"]:not(:disabled)',
    ),
  );
}

const MENU_ITEM_MOVES: Readonly<
  Record<string, (index: number, length: number) => number>
> = {
  ArrowDown: (index, length) => (index + 1) % length,
  ArrowUp: (index, length) => (index - 1 + length) % length,
  Home: () => 0,
  End: (_index, length) => length - 1,
};

function moveMenuFocus(
  menu: HTMLElement | null,
  active: Element | null,
  move: (index: number, length: number) => number,
): void {
  const items = enabledMenuItems(menu);
  const first = items[0];
  if (first === undefined) {
    menu?.focus();
    return;
  }
  const index = active === null ? -1 : items.indexOf(active as HTMLElement);
  if (index === -1) {
    first.focus();
    return;
  }
  items[move(index, items.length)]?.focus();
}

/**
 * Closes the menu on an outside press and when any scroll (the column's own
 * body included, via the capture phase) or a resize moves the viewport away
 * from the fixed-position menu.
 */
function useMenuDismissal(
  open: boolean,
  close: () => void,
  refs: MenuDismissalRefs,
): void {
  const { menuRef, triggerRef } = refs;
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: MouseEvent): void => {
      const target = event.target;
      if (!(target instanceof Node)) return;
      if (menuRef.current?.contains(target) === true) return;
      if (triggerRef.current?.contains(target) === true) return;
      close();
    };
    document.addEventListener("mousedown", onPointerDown);
    window.addEventListener("scroll", close, true);
    window.addEventListener("resize", close);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      window.removeEventListener("scroll", close, true);
      window.removeEventListener("resize", close);
    };
  }, [open, close, menuRef, triggerRef]);
}

/**
 * Focuses the first enabled menu item whenever the menu opens or its content
 * swaps (the archive confirmation), falling back to the menu container when
 * every item is disabled.
 */
function useMenuItemFocus(
  open: boolean,
  confirming: boolean,
  menuRef: RefObject<HTMLDivElement | null>,
): void {
  useEffect(() => {
    if (!open) return;
    moveMenuFocus(menuRef.current, null, () => 0);
  }, [open, confirming, menuRef]);
}

function handleMenuKeyDown(
  event: KeyboardEvent<HTMLDivElement>,
  menuRef: RefObject<HTMLDivElement | null>,
  closeMenu: (returnFocus: boolean) => void,
): void {
  if (event.key === "Escape") {
    event.preventDefault();
    closeMenu(true);
    return;
  }
  if (event.key === "Tab") {
    closeMenu(false);
    return;
  }
  const move = MENU_ITEM_MOVES[event.key];
  if (move === undefined) return;
  event.preventDefault();
  moveMenuFocus(menuRef.current, document.activeElement, move);
}

function handleMenuBlur(
  event: FocusEvent<HTMLDivElement>,
  closeMenu: (returnFocus: boolean) => void,
): void {
  const next = event.relatedTarget;
  if (next === null) return;
  if (next instanceof Node && event.currentTarget.contains(next)) return;
  closeMenu(false);
}

/**
 * The behavior of a card's overflow menu shell: open/close state, fixed
 * position from the trigger rect, dismissal, focus management and keyboard
 * navigation.
 */
export function useCardOverflowMenu(): CardOverflowMenu {
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const [open, setOpen] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [position, setPosition] = useState<MenuPosition>({
    top: 0,
    left: 0,
  });

  const close = useCallback((): void => {
    setOpen(false);
    setConfirming(false);
  }, []);

  const closeMenu = useCallback(
    (returnFocus: boolean): void => {
      close();
      if (returnFocus) triggerRef.current?.focus();
    },
    [close],
  );

  const openMenu = useCallback((): void => {
    const trigger = triggerRef.current?.getBoundingClientRect();
    if (trigger !== undefined) setPosition(menuPosition(trigger));
    setOpen(true);
  }, []);

  useMenuDismissal(open, close, { menuRef, triggerRef });
  useMenuItemFocus(open, confirming, menuRef);

  const onMenuKeyDown = (event: KeyboardEvent<HTMLDivElement>): void => {
    handleMenuKeyDown(event, menuRef, closeMenu);
  };

  const onMenuBlur = (event: FocusEvent<HTMLDivElement>): void => {
    handleMenuBlur(event, closeMenu);
  };

  return {
    open,
    confirming,
    onConfirmingChange: setConfirming,
    triggerRef,
    menuRef,
    position,
    openMenu,
    closeMenu,
    onMenuKeyDown,
    onMenuBlur,
  };
}
