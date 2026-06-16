import { describe, it, expect } from "vitest";
import {
  mapApiKanbanColumn,
  mapWorkflowColumnDataToKanban,
  mapWorkflowToKanbanColumns,
} from "@/modules/editorial-operations/board/workflow/adapters/workflow-adapter";
import type { WorkflowColumnData } from "@/modules/editorial-operations/board/workflow/constants";

describe("workflow-adapter", () => {
  const column: WorkflowColumnData = {
    id: "research",
    label: "Research",
    color: "#00d4ff",
    cards: [
      {
        title: "Card A",
        description: "Desc",
        phase: "research",
        assignee: "PM",
        assigneeBg: "rgba(0,0,0,0.1)",
        assigneeColor: "#00d4ff",
        approvalStatus: "pending",
      },
    ],
  };

  it("mapWorkflowColumnDataToKanban maps dashboard columns", () => {
    const result = mapWorkflowColumnDataToKanban([column]);
    expect(result[0].status).toBe("Research");
    expect(result[0].cards[0].phaseStatus).toBe("pending");
    expect(result[0].cards[0].id).toBe("research-0");
  });

  it("mapWorkflowToKanbanColumns maps API-shaped columns", () => {
    const result = mapWorkflowToKanbanColumns([
      {
        phase: "research",
        status: "Research",
        cards: [
          {
            id: "uuid-1",
            title: "Card",
            description: "D",
            phase: "research",
            phaseStatus: "active",
          },
        ],
      },
    ]);
    expect(result[0].cards[0].id).toBe("uuid-1");
  });

  it("mapApiKanbanColumn prefers workflow_status over phase_status", () => {
    const result = mapApiKanbanColumn({
      phase: "final_review",
      cards: [
        {
          id: "proj-1",
          title: "Carousel",
          topic: "AI",
          current_phase: "final_review",
          phase_status: "awaiting_human",
          workflow_status: "approved_for_publish",
          updated_at: null,
        },
      ],
    });
    expect(result.cards[0].phaseStatus).toBe("approved_for_publish");
  });

  it("mapApiKanbanColumn falls back to phase_status when workflow_status absent", () => {
    const result = mapApiKanbanColumn({
      phase: "outline",
      cards: [
        {
          id: "proj-2",
          title: "Draft",
          topic: "Topic",
          current_phase: "outline",
          phase_status: "in_progress",
          updated_at: null,
        },
      ],
    });
    expect(result.cards[0].phaseStatus).toBe("in_progress");
  });
});
