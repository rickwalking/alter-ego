import { describe, it, expect } from "vitest";
import {
  mapWorkflowColumnDataToKanban,
  mapWorkflowToKanbanColumns,
} from "@/features/dashboard/workflow/adapters/workflow-adapter";
import type { WorkflowColumnData } from "@/features/dashboard/workflow/constants";

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
});
