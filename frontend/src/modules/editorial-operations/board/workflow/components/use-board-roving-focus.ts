"use client";

import { useCallback, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import type { KanbanCard, KanbanColumn } from "@/schemas/neon-kanban";
import type { BoardRovingFocus } from "./types";

const CARD_LINK_SELECTOR = "a[data-board-card-id]";

type CardColumns = readonly (readonly KanbanCard[])[];

interface CardPosition {
  readonly column: number;
  readonly row: number;
}

interface BoardKeyResult {
  readonly click: boolean;
  readonly focusId: string | null;
}

function cardsAt(columns: CardColumns, index: number): readonly KanbanCard[] {
  return columns[index] ?? [];
}

function positionOf(columns: CardColumns, cardId: string): CardPosition | null {
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

function rowStep(columns: CardColumns, position: CardPosition, delta: number) {
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
  position: CardPosition,
  step: number,
): CardPosition | null {
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
  position: CardPosition,
  key: string,
): CardPosition | null {
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

interface BoardCardLink {
  readonly link: Element;
  readonly cardId: string;
}

function boardCardLink(target: EventTarget | null): BoardCardLink | null {
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
 * Roving tabindex across the board cards: exactly one card link stays in the
 * tab order and the arrow keys move the focus, scrolling the card into view
 * nearest-edge.
 */
export function useBoardRovingFocus(
  columns: readonly KanbanColumn[],
): BoardRovingFocus {
  const cardColumns = columns.map((column) => column.cards);
  const cardRefs = useRef(new Map<string, HTMLElement>());
  const [tabbableCardId, setTabbableCardId] = useTabbableCardId(cardColumns);

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

  return { tabbableCardId, registerCard, onBoardKeyDown };
}
