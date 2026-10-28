import { beforeEach, describe, expect, it } from "vitest";
import {
  boardSequenceSnapshot,
  loadBoardSequence,
  saveBoardSequence,
} from "@/modules/editorial-operations/board/workflow/components/board-sequence";
import { WORKFLOW_BOARD_SEQUENCE_STORAGE_KEY } from "@/modules/editorial-operations/board/workflow/constants";

describe("board sequence persistence", () => {
  /** Scenario: Previous and next controls follow the board column sequence */
  it("round trips the localized column and ordered card ids", () => {
    saveBoardSequence("Final review", ["p1", "p2", "p3"]);
    expect(loadBoardSequence()).toEqual({
      column: "Final review",
      ids: ["p1", "p2", "p3"],
    });
  });

  /** Scenario: Previous and next controls follow the board column sequence */
  it("rejects malformed stored sequences", () => {
    window.sessionStorage.setItem(
      WORKFLOW_BOARD_SEQUENCE_STORAGE_KEY,
      JSON.stringify({ column: "Final review", ids: [1] }),
    );
    expect(loadBoardSequence()).toBeNull();
  });

  it("rejects null and non-object payloads", () => {
    window.sessionStorage.setItem(
      WORKFLOW_BOARD_SEQUENCE_STORAGE_KEY,
      JSON.stringify(null),
    );
    expect(loadBoardSequence()).toBeNull();
    window.sessionStorage.setItem(WORKFLOW_BOARD_SEQUENCE_STORAGE_KEY, "3");
    expect(loadBoardSequence()).toBeNull();
  });

  it("caches the snapshot until the stored value changes", () => {
    saveBoardSequence("Final review", ["p1"]);
    const first = boardSequenceSnapshot();
    expect(boardSequenceSnapshot()).toBe(first);
    saveBoardSequence("Published", ["p9"]);
    const second = boardSequenceSnapshot();
    expect(second).not.toBe(first);
    expect(second).toEqual({ column: "Published", ids: ["p9"] });
  });

  it("never throws when the storage is unavailable", () => {
    const original = window.sessionStorage;
    const boom = (): never => {
      throw new Error("storage disabled");
    };
    Object.defineProperty(window, "sessionStorage", {
      value: {
        getItem: boom,
        setItem: boom,
        removeItem: boom,
      },
      configurable: true,
    });
    try {
      expect(() => saveBoardSequence("x", [])).not.toThrow();
      expect(loadBoardSequence()).toBeNull();
      expect(boardSequenceSnapshot()).toBeNull();
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
