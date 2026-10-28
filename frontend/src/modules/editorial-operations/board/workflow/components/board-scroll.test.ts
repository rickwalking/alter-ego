import { describe, it, expect, beforeEach } from "vitest";
import {
  applyBoardScroll,
  boardScrollStorageKey,
  loadSavedBoardScroll,
  saveBoardScroll,
} from "@/modules/editorial-operations/board/workflow/components/board-scroll";
import { WORKFLOW_BOARD_SCROLL_STORAGE_PREFIX } from "@/modules/editorial-operations/board/workflow/constants";

interface ScrollElement {
  scrollLeft: number;
  scrollTop: number;
}

function disabledSessionStorage(): Storage {
  const boom = (): never => {
    throw new Error("storage disabled");
  };
  return {
    getItem: boom,
    setItem: boom,
    removeItem: boom,
    clear: boom,
    key: boom,
    length: 0,
  };
}

describe("board scroll persistence", () => {
  /** Scenario: Returning from a carousel restores the board scroll */
  it("saves the board and column positions under its view key", () => {
    const board = { scrollLeft: 148, scrollTop: 0 };
    saveBoardScroll(board as HTMLElement, { research: 220 }, "active");
    expect(boardScrollStorageKey("active")).toBe(
      `${WORKFLOW_BOARD_SCROLL_STORAGE_PREFIX}:active`,
    );
    expect(
      JSON.parse(
        window.sessionStorage.getItem(
          `${WORKFLOW_BOARD_SCROLL_STORAGE_PREFIX}:active`,
        ) ?? "{}",
      ),
    ).toEqual({ left: 148, tops: { research: 220 } });
  });

  /** Scenario: Returning from a carousel restores the board scroll */
  it("keeps the active and archived views apart", () => {
    saveBoardScroll(
      { scrollLeft: 10, scrollTop: 0 } as HTMLElement,
      {},
      "active",
    );
    saveBoardScroll(
      { scrollLeft: 90, scrollTop: 0 } as HTMLElement,
      {},
      "archived",
    );
    expect(loadSavedBoardScroll("active")?.left).toBe(10);
    expect(loadSavedBoardScroll("archived")?.left).toBe(90);
  });

  /** Scenario: Returning from a carousel restores the board scroll */
  it("restores a saved position once and clears it", () => {
    const board: ScrollElement = { scrollLeft: 0, scrollTop: 0 };
    const research: ScrollElement = { scrollLeft: 0, scrollTop: 0 };
    window.sessionStorage.setItem(
      `${WORKFLOW_BOARD_SCROLL_STORAGE_PREFIX}:active`,
      JSON.stringify({ left: 42, tops: { research: 7 } }),
    );
    expect(loadSavedBoardScroll("active")).toEqual({
      left: 42,
      tops: { research: 7 },
    });
    applyBoardScroll({
      board: board as HTMLElement,
      columns: { research: research as HTMLElement },
      position: { left: 42, tops: { research: 7 } },
      view: "active",
    });
    expect(board.scrollLeft).toBe(42);
    expect(research.scrollTop).toBe(7);
    expect(
      window.sessionStorage.getItem(
        `${WORKFLOW_BOARD_SCROLL_STORAGE_PREFIX}:active`,
      ),
    ).toBeNull();
  });

  /** Scenario: Returning from a carousel restores the board scroll */
  it("returns no saved position when nothing valid is stored", () => {
    window.sessionStorage.setItem(
      `${WORKFLOW_BOARD_SCROLL_STORAGE_PREFIX}:active`,
      "not json",
    );
    expect(loadSavedBoardScroll("active")).toBeNull();
  });

  /** Scenario: Returning from a carousel restores the board scroll */
  it("rejects corrupt payloads instead of breaking the board", () => {
    const key = `${WORKFLOW_BOARD_SCROLL_STORAGE_PREFIX}:active`;
    for (const payload of [
      JSON.stringify(null),
      JSON.stringify({ left: "x", tops: {} }),
      JSON.stringify({ left: 5, tops: null }),
      JSON.stringify({ left: 5 }),
      JSON.stringify([1, 2]),
    ]) {
      window.sessionStorage.setItem(key, payload);
      expect(loadSavedBoardScroll("active")).toBeNull();
    }
  });

  it("drops non-number column tops from an otherwise valid payload", () => {
    window.sessionStorage.setItem(
      `${WORKFLOW_BOARD_SCROLL_STORAGE_PREFIX}:active`,
      JSON.stringify({ left: 5, tops: { a: "x", b: 3 } }),
    );
    expect(loadSavedBoardScroll("active")).toEqual({ left: 5, tops: { b: 3 } });
  });

  it("never throws when the storage is disabled or full", () => {
    const original = window.sessionStorage;
    Object.defineProperty(window, "sessionStorage", {
      value: disabledSessionStorage(),
      configurable: true,
    });
    try {
      expect(() =>
        saveBoardScroll(
          { scrollLeft: 1, scrollTop: 0 } as HTMLElement,
          {},
          "active",
        ),
      ).not.toThrow();
      expect(loadSavedBoardScroll("active")).toBeNull();
      expect(() =>
        applyBoardScroll({
          board: { scrollLeft: 0, scrollTop: 0 } as HTMLElement,
          columns: {},
          position: { left: 0, tops: {} },
          view: "active",
        }),
      ).not.toThrow();
    } finally {
      Object.defineProperty(window, "sessionStorage", {
        value: original,
        configurable: true,
      });
    }
  });

  beforeEach(() => {
    window.sessionStorage.clear();
  });
});
