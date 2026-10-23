/** The archive refusal and permission the board API reports for each card. */
import { describe, expect, it } from "vitest";
import type { KanbanCard } from "@/modules/editorial";
import { archiveRefusalOf, mapApiKanbanColumn } from "./workflow-adapter";

function apiCard(overrides: Partial<KanbanCard> = {}): KanbanCard {
  return {
    id: "proj-1",
    title: "Carousel",
    topic: "AI",
    current_phase: "content",
    phase_status: "in_progress",
    updated_at: null,
    ...overrides,
  };
}

describe("archiveRefusalOf", () => {
  /** Scenario: A published card has no archive control */
  it("passes the server's published refusal through", () => {
    expect(archiveRefusalOf(apiCard({ archive_refusal: "published" }))).toBe(
      "published",
    );
  });

  /** Scenario: A card in progress cannot be archived */
  it("passes the server's running and autopilot refusals through", () => {
    expect(archiveRefusalOf(apiCard({ archive_refusal: "in_progress" }))).toBe(
      "in_progress",
    );
    expect(archiveRefusalOf(apiCard({ archive_refusal: "autopilot" }))).toBe(
      "autopilot",
    );
  });

  /** Scenario: A phase stuck with a stale heartbeat can be archived */
  it("allows a card the server does not refuse, even one in progress", () => {
    expect(archiveRefusalOf(apiCard({ archive_refusal: null }))).toBeNull();
    expect(archiveRefusalOf(apiCard())).toBeNull();
    expect(
      archiveRefusalOf(apiCard({ archive_refusal: "unknown" })),
    ).toBeNull();
  });
});

describe("mapApiKanbanColumn archive fields", () => {
  /** Scenario: A reviewer sees no archive control */
  it("maps can_archive, defaulting to false", () => {
    const column = mapApiKanbanColumn({
      phase: "content",
      cards: [apiCard({ id: "a", can_archive: true }), apiCard({ id: "b" })],
    });
    expect(column.cards.map((card) => card.canArchive)).toEqual([true, false]);
  });
});
