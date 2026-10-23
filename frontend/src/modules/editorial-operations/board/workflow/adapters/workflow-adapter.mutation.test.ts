import { describe, it, expect } from "vitest";
import {
  mapApiKanbanColumn,
  mapApiWorkflowKanbanToNeon,
  mapWorkflowColumnDataToKanban,
  mapWorkflowToKanbanColumns,
} from "@/modules/editorial-operations/board/workflow/adapters/workflow-adapter";
import type { WorkflowColumnData } from "@/modules/editorial-operations/board/workflow/constants";
import type { KanbanCard, WorkflowKanban } from "@/modules/editorial";

const DASHBOARD_COLUMN: WorkflowColumnData = {
  id: "research",
  label: "Research",
  color: "#00d4ff",
  cards: [
    {
      title: "Card A",
      description: "Desc A",
      phase: "research",
      assignee: "PM",
      assigneeBg: "rgba(0,0,0,0.1)",
      assigneeColor: "#00d4ff",
      approvalStatus: "pending",
    },
    {
      title: "Card B",
      description: "Desc B",
      phase: "research",
      assignee: "QA",
      assigneeBg: "rgba(0,0,0,0.1)",
      assigneeColor: "#00d4ff",
      approvalStatus: "approved",
    },
  ],
};

function makeApiCard(overrides: Partial<KanbanCard> = {}): KanbanCard {
  return {
    id: "proj-1",
    title: "Carousel",
    topic: "AI",
    current_phase: "final_review",
    phase_status: "awaiting_human",
    updated_at: null,
    ...overrides,
  };
}

describe("mapWorkflowColumnDataToKanban", () => {
  /** Scenario: Kanban renders column status labels */
  it("maps every column and card field with index based ids", () => {
    expect(mapWorkflowColumnDataToKanban([DASHBOARD_COLUMN])).toEqual([
      {
        phase: "research",
        status: "Research",
        count: 2,
        cards: [
          {
            id: "research-0",
            title: "Card A",
            description: "Desc A",
            phase: "research",
            phaseStatus: "pending",
            assignee: "PM",
          },
          {
            id: "research-1",
            title: "Card B",
            description: "Desc B",
            phase: "research",
            phaseStatus: "approved",
            assignee: "QA",
          },
        ],
      },
    ]);
  });
});

describe("mapWorkflowToKanbanColumns", () => {
  /** Scenario: Kanban renders card titles */
  it("copies every column and card field", () => {
    const card = {
      id: "uuid-1",
      title: "Card",
      description: "D",
      phase: "research",
      phaseStatus: "active",
      assignee: "PM",
    };
    expect(
      mapWorkflowToKanbanColumns([
        { phase: "research", status: "Research", cards: [card] },
      ]),
    ).toEqual([
      { phase: "research", status: "Research", count: 1, cards: [card] },
    ]);
  });
});

describe("mapApiKanbanColumn", () => {
  it("title-cases every underscore separated word of the phase label", () => {
    const result = mapApiKanbanColumn({
      phase: "final_review_gate",
      cards: [],
    });
    expect(result).toEqual({
      phase: "final_review_gate",
      status: "Final Review Gate",
      count: 0,
      cards: [],
    });
  });

  it("maps the topic and current phase of each card", () => {
    const result = mapApiKanbanColumn({
      phase: "final_review",
      cards: [makeApiCard({ workflow_status: null })],
    });
    expect(result.count).toBe(1);
    expect(result.cards).toEqual([
      {
        id: "proj-1",
        title: "Carousel",
        description: "AI",
        phase: "final_review",
        phaseStatus: "awaiting_human",
        archiveRefusal: null,
        canArchive: false,
      },
    ]);
  });
});

describe("mapApiWorkflowKanbanToNeon", () => {
  it("maps every board column in order", () => {
    const board: WorkflowKanban = {
      columns: [
        { phase: "research", cards: [makeApiCard({ id: "a" })] },
        { phase: "outline", cards: [] },
      ],
    };
    const result = mapApiWorkflowKanbanToNeon(board);
    expect(result.map((column) => column.status)).toEqual([
      "Research",
      "Outline",
    ]);
    expect(result.map((column) => column.count)).toEqual([1, 0]);
    expect(result[0]!.cards[0]!.id).toBe("a");
  });
});
