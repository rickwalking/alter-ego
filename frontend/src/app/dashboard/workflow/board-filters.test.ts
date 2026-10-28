import { describe, expect, it } from "vitest";
import type { KanbanColumn } from "@/schemas/neon-kanban";
import {
  DEFAULT_BOARD_FILTERS,
  boardFiltersHref,
  boardStatusBucket,
  countBoardStatusBuckets,
  filterBoardColumns,
  normalizeBoardText,
  parseBoardFilters,
} from "@/app/dashboard/workflow/board-filters";

function card(
  overrides: Record<string, unknown> = {},
): KanbanColumn["cards"][0] {
  return {
    id: "c1",
    title: "Opinião impopular",
    description: "Claude",
    phase: "final_review",
    phaseStatus: "Precisa de você",
    statusKey: "awaiting_human",
    updatedAt: "2026-10-20T10:00:00Z",
    ...overrides,
  };
}

function columnsOf(cards: KanbanColumn["cards"]): KanbanColumn[] {
  return [
    {
      phase: "final_review",
      status: "Final review",
      count: cards.length,
      cards,
    },
  ];
}

describe("board filters", () => {
  it("normalizes case and accents", () => {
    expect(normalizeBoardText("Instável CAFÉ")).toBe("instavel cafe");
  });

  it("buckets raw statuses into filter groups", () => {
    expect(boardStatusBucket("awaiting_human")).toBe("needsReview");
    expect(boardStatusBucket("in_progress")).toBe("inProgress");
    expect(boardStatusBucket("approved_for_publish")).toBe("ready");
    expect(boardStatusBucket("rejected")).toBe("failed");
    expect(boardStatusBucket("some_new_status")).toBe("all");
  });

  /** Scenario: Search narrows the board */
  it("keeps only cards whose title or topic matches, accent-insensitively", () => {
    const columns = columnsOf([
      card({ id: "a", title: "Instável no Claude" }),
      card({ id: "b", title: "Outro", description: "vender online" }),
      card({ id: "c", title: "", description: "" }),
    ]);
    const filtered = filterBoardColumns(columns, {
      ...DEFAULT_BOARD_FILTERS,
      query: "instavel",
    });
    expect(filtered[0]?.cards.map((item) => item.id)).toEqual(["a"]);
    expect(filtered[0]?.count).toBe(1);
  });

  /** Scenario: Status chips filter by raw status */
  it("keeps only the cards of the pressed bucket", () => {
    const columns = columnsOf([
      card({ id: "a", statusKey: "awaiting_human" }),
      card({ id: "b", statusKey: "in_progress" }),
      card({ id: "c", statusKey: "rejected" }),
    ]);
    const filtered = filterBoardColumns(columns, {
      ...DEFAULT_BOARD_FILTERS,
      status: "failed",
    });
    expect(filtered[0]?.cards.map((item) => item.id)).toEqual(["c"]);
  });

  /** Scenario: The board keeps a stable newest-first order */
  it("sorts by updated time descending with nulls last and id tiebreak", () => {
    const columns = columnsOf([
      card({ id: "old", updatedAt: "2026-10-18T10:00:00Z" }),
      card({ id: "bbb", updatedAt: "2026-10-20T10:00:00Z" }),
      card({ id: "aaa", updatedAt: "2026-10-20T10:00:00Z" }),
      card({ id: "none", updatedAt: null }),
      card({ id: "new", updatedAt: "2026-10-24T10:00:00Z" }),
    ]);
    const filtered = filterBoardColumns(columns, DEFAULT_BOARD_FILTERS);
    expect(filtered[0]?.cards.map((item) => item.id)).toEqual([
      "new",
      "aaa",
      "bbb",
      "old",
      "none",
    ]);
  });

  /** Scenario: Sort follows the toolbar */
  it("sorts by title when chosen", () => {
    const columns = columnsOf([
      card({ id: "b", title: "Beta" }),
      card({ id: "a", title: "Alfa" }),
    ]);
    const filtered = filterBoardColumns(columns, {
      ...DEFAULT_BOARD_FILTERS,
      sort: "title",
    });
    expect(filtered[0]?.cards.map((item) => item.id)).toEqual(["a", "b"]);
  });

  it("counts every bucket over the unfiltered board", () => {
    const counts = countBoardStatusBuckets(
      columnsOf([
        card({ statusKey: "awaiting_human" }),
        card({ statusKey: "awaiting_human" }),
        card({ statusKey: "in_progress" }),
        card({ statusKey: "approved_for_publish" }),
        card({ statusKey: "rejected" }),
      ]),
    );
    expect(counts).toEqual({
      all: 5,
      needsReview: 2,
      inProgress: 1,
      ready: 1,
      failed: 1,
    });
  });

  /** Scenario: Status chips filter by raw status */
  it("counts an unmapped status only once, in the total", () => {
    const counts = countBoardStatusBuckets(
      columnsOf([
        card({ statusKey: "published" }),
        card({ statusKey: "draft" }),
        card({ statusKey: "some_new_status" }),
      ]),
    );
    expect(counts.all).toBe(3);
    expect(counts).toEqual({
      all: 3,
      needsReview: 0,
      inProgress: 0,
      ready: 0,
      failed: 0,
    });
  });

  /** Scenario: Sort follows the toolbar */
  it("sorts by title in the dashboard locale with an id tiebreak", () => {
    const columns = columnsOf([
      card({ id: "b", title: "Água" }),
      card({ id: "c", title: "Azul" }),
      card({ id: "a2", title: "Beta" }),
      card({ id: "a1", title: "Beta" }),
    ]);
    const filtered = filterBoardColumns(
      columns,
      { ...DEFAULT_BOARD_FILTERS, sort: "title" },
      "pt-BR",
    );
    expect(filtered[0]?.cards.map((item) => item.id)).toEqual([
      "b",
      "c",
      "a1",
      "a2",
    ]);
  });

  it("parses valid URL values and falls back to defaults", () => {
    const params = new URLSearchParams("q=claude&status=ready&sort=title");
    expect(parseBoardFilters(params)).toEqual({
      query: "claude",
      status: "ready",
      sort: "title",
    });
    expect(parseBoardFilters(new URLSearchParams("status=bogus"))).toEqual(
      DEFAULT_BOARD_FILTERS,
    );
  });

  it("keeps default values out of the href", () => {
    expect(boardFiltersHref("/dashboard/workflow", DEFAULT_BOARD_FILTERS)).toBe(
      "/dashboard/workflow",
    );
    expect(
      boardFiltersHref("/dashboard/workflow", {
        query: "claude",
        status: "ready",
        sort: "title",
      }),
    ).toBe("/dashboard/workflow?q=claude&status=ready&sort=title");
  });
});
