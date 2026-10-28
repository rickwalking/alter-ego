import { beforeEach, describe, expect, it } from "vitest";
import {
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

  beforeEach(() => {
    window.sessionStorage.clear();
  });
});
