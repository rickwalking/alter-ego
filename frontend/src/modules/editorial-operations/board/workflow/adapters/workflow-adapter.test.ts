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
    expect(result[0]!.status).toBe("Research");
    expect(result[0]!.cards[0]!.phaseStatus).toBe("pending");
    expect(result[0]!.cards[0]!.id).toBe("research-0");
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
    expect(result[0]!.cards[0]!.id).toBe("uuid-1");
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
    expect(result.cards[0]!.phaseStatus).toBe("approved_for_publish");
    expect(result.cards[0]!.statusKey).toBe("approved_for_publish");
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
    expect(result.cards[0]!.phaseStatus).toBe("in_progress");
  });

  /** Scenario: Card titles are readable */
  it("mapApiKanbanColumn strips inline markup from titles and topics", () => {
    const result = mapApiKanbanColumn({
      phase: "content",
      cards: [
        {
          id: "proj-3",
          title: "É **anúncio**.",
          topic: "Por que <strong>ChatGPT</strong> e não o __Claude__?",
          current_phase: "content",
          phase_status: "in_progress",
          updated_at: null,
        },
      ],
    });
    expect(result.cards[0]!.title).toBe("É anúncio.");
    expect(result.cards[0]!.description).toBe(
      "Por que ChatGPT e não o Claude?",
    );
  });

  /** Scenario: Card titles are readable */
  it("mapApiKanbanColumn falls back to the topic and blanks repeated descriptions", () => {
    const result = mapApiKanbanColumn({
      phase: "rejected",
      cards: [
        {
          id: "proj-4",
          title: "",
          topic: "",
          current_phase: "brief",
          phase_status: "rejected",
          updated_at: null,
        },
        {
          id: "proj-5",
          title: "GPT 5.6 saiu",
          topic: "GPT 5.6 saiu",
          current_phase: "published",
          phase_status: "approved_for_publish",
          updated_at: null,
        },
      ],
    });
    expect(result.cards[0]!.title).toBe("");
    expect(result.cards[0]!.description).toBe("");
    expect(result.cards[1]!.description).toBe("");
  });

  /** Scenario: The board keeps a stable newest-first order */
  it("mapApiKanbanColumn keeps the API updated_at for sorting and recency", () => {
    const result = mapApiKanbanColumn({
      phase: "published",
      cards: [
        {
          id: "proj-6",
          title: "Published",
          topic: "topic",
          current_phase: "published",
          phase_status: "approved_for_publish",
          updated_at: "2026-10-24T12:00:00Z",
        },
      ],
    });
    expect(result.cards[0]!.updatedAt).toBe("2026-10-24T12:00:00Z");
  });
});
