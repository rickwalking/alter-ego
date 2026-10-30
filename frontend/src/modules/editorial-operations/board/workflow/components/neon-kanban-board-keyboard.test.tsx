/** Roving keyboard navigation across the workflow board cards. */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { NeonKanbanBoard } from "@/modules/editorial-operations";
import type { BoardColumnLabels } from "@/modules/editorial-operations/board/workflow/components/types";
import type { KanbanCard, KanbanColumn } from "@/schemas/neon-kanban";

vi.mock("next-intl", () => ({
  useLocale: () => "pt",
  useTranslations: () => (key: string) => key,
}));

const labels: BoardColumnLabels = {
  emptyColumn: "Nenhum projeto",
  expandColumn: (name: string, count: number) =>
    `Expandir coluna ${name} (${count})`,
  collapseColumn: (name: string) => `Recolher coluna ${name}`,
  needYou: (count: number) => `${count} precisam de você`,
  columnCount: (count: number) => `${count} itens`,
};

function card(id: string, phase: string): KanbanCard {
  return {
    id,
    title: `Card ${id}`,
    description: "topic",
    phase,
    phaseStatus: "in_progress",
    statusKey: "in_progress",
  };
}

function boardColumns(): KanbanColumn[] {
  return [
    {
      phase: "research",
      status: "Research",
      count: 2,
      cards: [card("r-0", "research"), card("r-1", "research")],
    },
    { phase: "brief", status: "Brief", count: 0, cards: [] },
    {
      phase: "content",
      status: "Content",
      count: 3,
      cards: [
        card("c-0", "content"),
        card("c-1", "content"),
        card("c-2", "content"),
      ],
    },
    {
      phase: "images",
      status: "Images",
      count: 1,
      cards: [card("i-0", "images")],
    },
  ];
}

function link(id: string): HTMLElement {
  return screen.getByRole("link", { name: `Card ${id}, in_progress` });
}

function renderBoard(): void {
  render(<NeonKanbanBoard columns={boardColumns()} labels={labels} />);
}

function tabbableLinks(): HTMLElement[] {
  return screen
    .getAllByRole("link")
    .filter((element) => element.getAttribute("tabindex") === "0");
}

describe("NeonKanbanBoard keyboard navigation", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  /** Scenario: The card grid costs one tab stop and arrows move between cards */
  it("keeps exactly one card in the tab order, the first card of the first non-empty column", () => {
    renderBoard();
    expect(tabbableLinks()).toHaveLength(1);
    expect(link("r-0")).toHaveAttribute("tabindex", "0");
    expect(link("r-1")).toHaveAttribute("tabindex", "-1");
    expect(link("c-0")).toHaveAttribute("tabindex", "-1");
    expect(link("i-0")).toHaveAttribute("tabindex", "-1");
  });

  /** Scenario: The card grid costs one tab stop and arrows move between cards */
  it("moves Down and Up within the column and clamps at the edges", () => {
    renderBoard();
    fireEvent.keyDown(link("r-0"), { key: "ArrowDown" });
    expect(link("r-1")).toHaveFocus();
    expect(link("r-1")).toHaveAttribute("tabindex", "0");
    expect(link("r-0")).toHaveAttribute("tabindex", "-1");

    fireEvent.keyDown(link("r-1"), { key: "ArrowUp" });
    expect(link("r-0")).toHaveFocus();

    fireEvent.keyDown(link("r-0"), { key: "ArrowUp" });
    expect(link("r-0")).toHaveFocus();
  });

  /** Scenario: The card grid costs one tab stop and arrows move between cards */
  it("jumps Left and Right to the same index in the adjacent non-empty column", () => {
    renderBoard();
    fireEvent.keyDown(link("r-1"), { key: "ArrowRight" });
    expect(link("c-1")).toHaveFocus();

    fireEvent.keyDown(link("c-1"), { key: "ArrowLeft" });
    expect(link("r-1")).toHaveFocus();
  });

  /** Scenario: The card grid costs one tab stop and arrows move between cards */
  it("clamps the column jump when the target column is shorter", () => {
    renderBoard();
    fireEvent.keyDown(link("c-2"), { key: "ArrowRight" });
    expect(link("i-0")).toHaveFocus();

    fireEvent.keyDown(link("i-0"), { key: "ArrowRight" });
    expect(link("i-0")).toHaveFocus();

    fireEvent.keyDown(link("c-0"), { key: "ArrowLeft" });
    expect(link("r-0")).toHaveFocus();

    fireEvent.keyDown(link("r-0"), { key: "ArrowLeft" });
    expect(link("r-0")).toHaveFocus();
  });

  /** Scenario: The card grid costs one tab stop and arrows move between cards */
  it("goes to the first and last card of the column with Home and End", () => {
    renderBoard();
    fireEvent.keyDown(link("c-1"), { key: "End" });
    expect(link("c-2")).toHaveFocus();

    fireEvent.keyDown(link("c-2"), { key: "Home" });
    expect(link("c-0")).toHaveFocus();
  });

  /** Scenario: The card grid costs one tab stop and arrows move between cards */
  it("opens the focused card with Enter", () => {
    renderBoard();
    let opened = false;
    const target = link("r-0");
    target.addEventListener("click", (event) => {
      event.preventDefault();
      opened = true;
    });

    fireEvent.keyDown(target, { key: "Enter" });

    expect(opened).toBe(true);
  });

  /** Scenario: A column announces itself and its count */
  it("announces the card count on the column list", () => {
    renderBoard();
    const section = screen.getByRole("region", { name: "Content" });
    expect(within(section).getByRole("list")).toHaveAttribute(
      "aria-label",
      "3 itens",
    );
  });

  /** Scenario: The card grid costs one tab stop and arrows move between cards */
  it("gives the card links the cyan focus ring", () => {
    renderBoard();
    expect(link("r-0").className).toContain("focus-visible:ring-neon-cyan");
  });

  /** Scenario: The card grid costs one tab stop and arrows move between cards */
  it("falls back to the first card when the focused card disappears", () => {
    const { rerender } = render(
      <NeonKanbanBoard columns={boardColumns()} labels={labels} />,
    );
    fireEvent.keyDown(link("c-2"), { key: "ArrowRight" });
    expect(link("i-0")).toHaveFocus();

    const withoutImages = boardColumns().filter(
      (column) => column.phase !== "images",
    );
    rerender(<NeonKanbanBoard columns={withoutImages} labels={labels} />);

    expect(link("r-0")).toHaveAttribute("tabindex", "0");
  });
});
