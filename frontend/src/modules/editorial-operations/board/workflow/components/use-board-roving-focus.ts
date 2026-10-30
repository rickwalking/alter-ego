"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import type { KanbanCard, KanbanColumn } from "@/schemas/neon-kanban";
import type {
  BoardCardFocus,
  BoardCardLinkTarget,
  BoardCardPosition,
  BoardKeyResult,
  BoardRovingFocus,
} from "./types";

const CARD_LINK_SELECTOR = "a[data-board-card-id]";

type CardColumns = readonly (readonly KanbanCard[])[];

function cardsAt(columns: CardColumns, index: number): readonly KanbanCard[] {
  return columns[index] ?? [];
}

function positionOf(
  columns: CardColumns,
  cardId: string,
): BoardCardPosition | null {
  for (let column = 0; column < columns.length; column += 1) {
    const row = cardsAt(columns, column).findIndex(
      (card) => card.id === cardId,
    );
    if (row !== -1) return { column, row };
  }
  return null;
}

function firstCardId(columns: CardColumns): string | null {
  for (const cards of columns) {
    const first = cards[0];
    if (first !== undefined) return first.id;
  }
  return null;
}

function clampRow(row: number, length: number): number {
  return Math.min(Math.max(row, 0), Math.max(length - 1, 0));
}

function rowStep(
  columns: CardColumns,
  position: BoardCardPosition,
  delta: number,
) {
  return {
    column: position.column,
    row: clampRow(
      position.row + delta,
      cardsAt(columns, position.column).length,
    ),
  };
}

function columnJump(
  columns: CardColumns,
  position: BoardCardPosition,
  step: number,
): BoardCardPosition | null {
  let column = position.column + step;
  while (
    column >= 0 &&
    column < columns.length &&
    cardsAt(columns, column).length === 0
  ) {
    column += step;
  }
  if (column < 0 || column >= columns.length) return null;
  return {
    column,
    row: clampRow(position.row, cardsAt(columns, column).length),
  };
}

function targetPosition(
  columns: CardColumns,
  position: BoardCardPosition,
  key: string,
): BoardCardPosition | null {
  if (key === "Home") return { column: position.column, row: 0 };
  if (key === "End") {
    return {
      column: position.column,
      row: Math.max(cardsAt(columns, position.column).length - 1, 0),
    };
  }
  if (key === "ArrowUp") return rowStep(columns, position, -1);
  if (key === "ArrowDown") return rowStep(columns, position, 1);
  if (key === "ArrowLeft") return columnJump(columns, position, -1);
  if (key === "ArrowRight") return columnJump(columns, position, 1);
  return null;
}

/**
 * Pure keyboard resolution for the board card grid: Enter clicks the card
 * link, the arrow keys move between cards (Up/Down within the column,
 * Left/Right to the adjacent non-empty column, Home/End to the column
 * edges), everything else is unhandled.
 */
function boardKeyResult(
  columns: CardColumns,
  cardId: string,
  key: string,
): BoardKeyResult | null {
  if (key === "Enter") return { click: true, focusId: null };
  const current = positionOf(columns, cardId);
  if (current === null) return null;
  const next = targetPosition(columns, current, key);
  if (next === null) return null;
  const card = cardsAt(columns, next.column)[next.row];
  if (card === undefined) return null;
  return { click: false, focusId: card.id };
}

function boardCardLink(target: EventTarget | null): BoardCardLinkTarget | null {
  if (!(target instanceof Element)) return null;
  const link = target.closest(CARD_LINK_SELECTOR);
  const cardId = link?.getAttribute("data-board-card-id");
  if (link === null || cardId === null || cardId === undefined) return null;
  return { link, cardId };
}

/**
 * The roving tab stop, derived during render: when the focused card
 * disappears (archive, poll refresh), the stop falls back to the first
 * card of the first non-empty column.
 */
function useTabbableCardId(
  cardColumns: CardColumns,
): readonly [string | null, (id: string) => void] {
  const [tabbableCardId, setTabbableCardId] = useState<string | null>(() =>
    firstCardId(cardColumns),
  );
  const fallbackId = firstCardId(cardColumns);
  if (
    tabbableCardId !== fallbackId &&
    positionOf(cardColumns, tabbableCardId ?? "") === null
  ) {
    setTabbableCardId(fallbackId);
  }
  return [tabbableCardId, setTabbableCardId];
}

/**
 * When the element that had focus leaves the board with its card (archive
 * from the menu, poll refresh, filter), the browser drops focus on the
 * body; move it to the roving fallback card. Focus outside the board (or
 * never inside it) is never pulled into the board.
 */
function useFocusRestoration(
  cardColumns: CardColumns,
  tabbableCardId: string | null,
  focusCard: (cardId: string) => void,
): void {
  const previousFocusRef = useRef<Element | null>(null);
  useEffect(() => {
    const rememberFocus = (): void => {
      previousFocusRef.current = document.activeElement;
    };
    document.addEventListener("focusin", rememberFocus);
    return () => document.removeEventListener("focusin", rememberFocus);
  }, []);

  useEffect(() => {
    const previous = previousFocusRef.current;
    previousFocusRef.current = document.activeElement;
    if (previous === null || previous === document.body) return;
    if (previous.isConnected) return;
    const active = document.activeElement;
    if (active !== null && active !== document.body && active.isConnected) {
      return;
    }
    if (tabbableCardId !== null) focusCard(tabbableCardId);
  }, [cardColumns, tabbableCardId, focusCard]);
}

/**
 * Focus moves between card links: the arrow-key handler resolves the target
 * and `focusCard` applies it, updates the roving stop and scrolls the card
 * into view nearest-edge.
 */
function useBoardCardFocus(
  cardColumns: CardColumns,
  setTabbableCardId: (id: string) => void,
): BoardCardFocus {
  const cardRefs = useRef(new Map<string, HTMLElement>());

  const registerCard = useCallback(
    (id: string, element: HTMLElement | null): void => {
      if (element === null) {
        cardRefs.current.delete(id);
      } else {
        cardRefs.current.set(id, element);
      }
    },
    [],
  );

  const focusCard = useCallback(
    (cardId: string): void => {
      const element = cardRefs.current.get(cardId);
      if (element === undefined) return;
      element.focus();
      setTabbableCardId(cardId);
      if (typeof element.scrollIntoView === "function") {
        element.scrollIntoView({ block: "nearest", inline: "nearest" });
      }
    },
    [setTabbableCardId],
  );

  const onBoardKeyDown = useCallback(
    (event: KeyboardEvent<HTMLElement>): void => {
      const cardLink = boardCardLink(event.target);
      if (cardLink === null) return;
      const result = boardKeyResult(cardColumns, cardLink.cardId, event.key);
      if (result === null) return;
      event.preventDefault();
      if (result.click) {
        cardLink.link.dispatchEvent(
          new MouseEvent("click", { bubbles: true, cancelable: true }),
        );
        return;
      }
      if (result.focusId !== null) focusCard(result.focusId);
    },
    [cardColumns, focusCard],
  );

  return { focusCard, onBoardKeyDown, registerCard };
}

/**
 * Roving tabindex across the board cards: exactly one card link stays in the
 * tab order; the arrow keys move the focus, scrolling the card into view.
 */
export function useBoardRovingFocus(
  columns: readonly KanbanColumn[],
): BoardRovingFocus {
  const cardColumns = useMemo(
    () => columns.map((column) => column.cards),
    [columns],
  );
  const [tabbableCardId, setTabbableCardId] = useTabbableCardId(cardColumns);
  const { focusCard, onBoardKeyDown, registerCard } = useBoardCardFocus(
    cardColumns,
    setTabbableCardId,
  );

  useFocusRestoration(cardColumns, tabbableCardId, focusCard);

  return { tabbableCardId, registerCard, onBoardKeyDown };
}
