import { describe, expect, it } from "vitest";
import type { KanbanColumn } from "@/schemas/neon-kanban";
import { localizeBoardColumns } from "./localize-board";

const translators = {
  phase: (key: string): string => `phase:${key}`,
  status: (key: string): string => `status:${key}`,
  knownPhases: new Set(["research", "final_review", "content"]),
  rejectedColumn: "Rejected",
};

function column(phase: string, statuses: string[]): KanbanColumn {
  return {
    phase,
    status: phase,
    count: statuses.length,
    cards: statuses.map((phaseStatus, index) => ({
      id: `${phase}-${index}`,
      title: "Card",
      description: "",
      phase,
      phaseStatus,
    })),
  };
}

// Feature: Create-flow UI fixes (AE-0415) — B24 board in the dashboard language
describe("localizeBoardColumns", () => {
  it("names columns by phase and cards by status label", () => {
    const [research, finalReview] = localizeBoardColumns(
      [
        column("research", ["awaiting_human"]),
        column("final_review", ["approved_for_publish", "rejected"]),
      ],
      translators,
    );
    expect(research.status).toBe("phase:research");
    expect(research.cards[0].phaseStatus).toBe("status:awaitingHuman");
    expect(finalReview.status).toBe("phase:final_review");
    expect(finalReview.cards.map((card) => card.phaseStatus)).toEqual([
      "status:readyToPublish",
      "status:rejected",
    ]);
  });

  it("titlecases unknown phases and statuses instead of throwing", () => {
    const [legacy] = localizeBoardColumns(
      [column("generating_images", ["some_new_status"])],
      translators,
    );
    expect(legacy.status).toBe("Generating Images");
    expect(legacy.cards[0].phaseStatus).toBe("Some New Status");
  });

  // Feature: QA follow-ups (AE-0416) — The board shows a localized Rejected column
  it("titles the rejected column and badges each card with its phase", () => {
    const rejected: KanbanColumn = {
      ...column("rejected", ["rejected", "rejected"]),
      cards: [
        { ...column("x", ["rejected"]).cards[0], phase: "content" },
        { ...column("x", ["rejected"]).cards[0], id: "y", phase: "legacy_x" },
      ],
    };
    const [localized] = localizeBoardColumns([rejected], translators);
    expect(localized.status).toBe("Rejected");
    expect(localized.cards.map((card) => card.phaseStatus)).toEqual([
      "phase:content",
      "Legacy X",
    ]);
  });
});
