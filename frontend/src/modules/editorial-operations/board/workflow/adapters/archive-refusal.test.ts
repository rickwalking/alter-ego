/** Which workflow board cards can be archived. */
import { describe, expect, it } from "vitest";
import type { KanbanCard } from "@/modules/editorial";
import { archiveRefusalOf } from "./workflow-adapter";

function apiCard(current_phase: string, phase_status: string): KanbanCard {
  return {
    id: "proj-1",
    title: "Carousel",
    topic: "AI",
    current_phase,
    phase_status,
    updated_at: null,
  };
}

describe("archiveRefusalOf", () => {
  /** Scenario: A published card has no archive control */
  it("refuses a published carousel", () => {
    expect(archiveRefusalOf(apiCard("published", "approved"))).toBe(
      "published",
    );
  });

  /** Scenario: A card in progress cannot be archived */
  it("refuses a carousel whose phase is in progress", () => {
    expect(archiveRefusalOf(apiCard("research", "in_progress"))).toBe(
      "in_progress",
    );
  });

  /** Scenario: Archiving a card asks for a confirmation first */
  it("allows any other carousel", () => {
    expect(archiveRefusalOf(apiCard("content", "awaiting_human"))).toBeNull();
    expect(archiveRefusalOf(apiCard("content", "failed"))).toBeNull();
  });
});
