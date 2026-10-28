import { describe, it, expect, beforeEach } from "vitest";
import {
  applyBoardScroll,
  loadSavedBoardScroll,
  saveBoardScroll,
} from "@/modules/editorial-operations/board/workflow/components/board-scroll";
import { WORKFLOW_BOARD_SCROLL_STORAGE_KEY } from "@/modules/editorial-operations/board/workflow/constants";

interface ScrollElement {
  scrollLeft: number;
  scrollTop: number;
}

describe("board scroll persistence", () => {
  /** Scenario: Returning from a carousel restores the board scroll */
  it("saves the board and column positions", () => {
    const board = { scrollLeft: 148, scrollTop: 0 };
    saveBoardScroll(board as HTMLElement, { research: 220, published: 15 });
    expect(
      JSON.parse(
        window.sessionStorage.getItem(WORKFLOW_BOARD_SCROLL_STORAGE_KEY) ??
          "{}",
      ),
    ).toEqual({ left: 148, tops: { research: 220, published: 15 } });
  });

  /** Scenario: Returning from a carousel restores the board scroll */
  it("restores a saved position once and clears it", () => {
    const board: ScrollElement = { scrollLeft: 0, scrollTop: 0 };
    const research: ScrollElement = { scrollLeft: 0, scrollTop: 0 };
    window.sessionStorage.setItem(
      WORKFLOW_BOARD_SCROLL_STORAGE_KEY,
      JSON.stringify({ left: 42, tops: { research: 7 } }),
    );
    expect(loadSavedBoardScroll()).toEqual({
      left: 42,
      tops: { research: 7 },
    });
    applyBoardScroll(
      board as HTMLElement,
      { research: research as HTMLElement },
      { left: 42, tops: { research: 7 } },
    );
    expect(board.scrollLeft).toBe(42);
    expect(research.scrollTop).toBe(7);
    expect(
      window.sessionStorage.getItem(WORKFLOW_BOARD_SCROLL_STORAGE_KEY),
    ).toBeNull();
  });

  /** Scenario: Returning from a carousel restores the board scroll */
  it("returns no saved position when nothing valid is stored", () => {
    window.sessionStorage.setItem(
      WORKFLOW_BOARD_SCROLL_STORAGE_KEY,
      "not json",
    );
    expect(loadSavedBoardScroll()).toBeNull();
  });

  beforeEach(() => {
    window.sessionStorage.clear();
  });
});
