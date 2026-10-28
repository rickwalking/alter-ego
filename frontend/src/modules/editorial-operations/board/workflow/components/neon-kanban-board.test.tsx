import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BADGE_COLORS, type NeonBadgeVariant } from "@/schemas/neon-badge";
import { NeonKanbanBoard } from "@/modules/editorial-operations";
import {
  WORKFLOW_BOARD_EXPANDED_STORAGE_KEY,
  WORKFLOW_BOARD_SCROLL_STORAGE_PREFIX,
  WORKFLOW_BOARD_SEQUENCE_STORAGE_KEY,
} from "@/modules/editorial-operations/board/workflow/constants";
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
};

function badgeColor(variant: NeonBadgeVariant): string {
  const hex = BADGE_COLORS[variant].text.replace("#", "");
  const value = Number.parseInt(hex, 16);
  const r = (value >> 16) & 0xff;
  const g = (value >> 8) & 0xff;
  const b = value & 0xff;
  return `rgb(${r}, ${g}, ${b})`;
}

function column(phase: string, status: string, cards: number): KanbanColumn {
  return cardsColumn(
    phase,
    status,
    Array.from({ length: cards }, (_, index) => ({
      id: `${phase}-${index}`,
      title: `${status} card ${index}`,
      description: "topic",
      phase,
      phaseStatus: "in_progress",
      statusKey: "in_progress",
    })),
  );
}

function cardsColumn(
  phase: string,
  status: string,
  cards: KanbanCard[],
): KanbanColumn {
  return { phase, status, count: cards.length, cards };
}

function boardScroll(): HTMLElement {
  return screen.getByTestId("workflow-board-scroll");
}

function columnList(phase: string): HTMLElement {
  return screen.getByTestId(`workflow-column-${phase}`);
}

describe("NeonKanbanBoard Component", () => {
  const columns = [
    cardsColumn("research", "Research", [
      {
        id: "card-1",
        title: "DeepSeek V4",
        description: "Research benchmarks",
        phase: "research",
        phaseStatus: "pending",
        statusKey: "pending",
        assignee: "PM",
      },
    ]),
  ];

  it("renders column status labels", () => {
    render(<NeonKanbanBoard columns={columns} labels={labels} />);
    expect(screen.getByText("Research")).toBeInTheDocument();
  });

  it("renders card titles", () => {
    render(<NeonKanbanBoard columns={columns} labels={labels} />);
    expect(screen.getByText("DeepSeek V4")).toBeInTheDocument();
  });

  /** Scenario: Archiving a card asks for a confirmation first */
  it("renders the card actions outside the card link", () => {
    render(
      <NeonKanbanBoard
        columns={columns}
        labels={labels}
        renderCardActions={(card) => (
          <button type="button">{`archive ${card.id}`}</button>
        )}
      />,
    );
    const action = screen.getByRole("button", { name: "archive card-1" });
    expect(action.closest("a")).toBeNull();
    expect(screen.getByRole("link")).toHaveTextContent("DeepSeek V4");
  });

  /** Scenario: The board fits the screen and columns scroll independently */
  it("keeps the board height fixed and scrolls each column on its own", () => {
    render(
      <NeonKanbanBoard
        columns={[column("research", "Research", 2)]}
        labels={labels}
      />,
    );
    expect(boardScroll().className).toContain("overflow-x-auto");
    expect(boardScroll().className).toContain("overflow-y-hidden");
    expect(columnList("research").className).toContain("overflow-y-auto");
  });

  /** Scenario: The board fits the screen and columns scroll independently */
  it("announces each column as a labelled list", () => {
    render(
      <NeonKanbanBoard
        columns={[column("research", "Research", 1)]}
        labels={labels}
      />,
    );
    const section = screen.getByRole("region", { name: "Research" });
    expect(section.tagName).toBe("SECTION");
    const list = within(section).getByRole("list");
    expect(within(list).getAllByRole("listitem")).toHaveLength(1);
    expect(list).toHaveTextContent("Research card 0");
  });

  /** Scenario: Empty and done columns collapse to rails */
  it("collapses empty and done columns into expandable rails", () => {
    render(
      <NeonKanbanBoard
        columns={[
          column("brief", "Brief", 0),
          column("research", "Research", 1),
          column("published", "Published", 3),
          column("rejected", "Rejected", 2),
        ]}
        labels={labels}
      />,
    );
    expect(
      screen.getByRole("button", { name: "Expandir coluna Brief (0)" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Expandir coluna Published (3)" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Expandir coluna Rejected (2)" }),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("workflow-column-published")).toBeNull();
    expect(screen.queryByTestId("workflow-column-rejected")).toBeNull();
    expect(screen.getByTestId("workflow-column-research")).not.toBeNull();
  });

  /** Scenario: Expanded rails persist across reloads */
  it("persists an expanded rail in localStorage", async () => {
    const user = userEvent.setup();
    render(
      <NeonKanbanBoard
        columns={[column("published", "Published", 2)]}
        labels={labels}
      />,
    );
    await user.click(
      screen.getByRole("button", { name: "Expandir coluna Published (2)" }),
    );
    expect(screen.getByTestId("workflow-column-published")).not.toBeNull();
    expect(
      JSON.parse(
        window.localStorage.getItem(WORKFLOW_BOARD_EXPANDED_STORAGE_KEY) ??
          "[]",
      ),
    ).toEqual(["published"]);
  });

  /** Scenario: Expanded rails persist across reloads */
  it("collapses an expanded column and persists the removal", async () => {
    const user = userEvent.setup();
    window.localStorage.setItem(
      WORKFLOW_BOARD_EXPANDED_STORAGE_KEY,
      JSON.stringify(["published"]),
    );
    render(
      <NeonKanbanBoard
        columns={[column("published", "Published", 2)]}
        labels={labels}
      />,
    );
    expect(screen.getByTestId("workflow-column-published")).not.toBeNull();
    await user.click(
      screen.getByRole("button", { name: "Recolher coluna Published" }),
    );
    expect(screen.queryByTestId("workflow-column-published")).toBeNull();
    expect(
      screen.getByRole("button", { name: "Expandir coluna Published (2)" }),
    ).toHaveAttribute("aria-expanded", "false");
    expect(
      JSON.parse(
        window.localStorage.getItem(WORKFLOW_BOARD_EXPANDED_STORAGE_KEY) ??
          "[]",
      ),
    ).toEqual([]);
  });

  it("exposes the expand and collapse state on both controls", async () => {
    const user = userEvent.setup();
    render(
      <NeonKanbanBoard
        columns={[column("published", "Published", 1)]}
        labels={labels}
      />,
    );
    const rail = screen.getByRole("button", {
      name: "Expandir coluna Published (1)",
    });
    expect(rail).toHaveAttribute("aria-expanded", "false");
    await user.click(rail);
    const collapse = screen.getByRole("button", {
      name: "Recolher coluna Published",
    });
    expect(collapse).toHaveAttribute("aria-expanded", "true");
  });

  /** Scenario: Returning from a carousel restores the board scroll */
  it("keeps card navigation working when the storage throws", async () => {
    const user = userEvent.setup();
    const original = window.sessionStorage;
    const boom = (): never => {
      throw new Error("storage disabled");
    };
    Object.defineProperty(window, "sessionStorage", {
      value: {
        getItem: boom,
        setItem: boom,
        removeItem: boom,
      },
      configurable: true,
    });
    let clicked = false;
    try {
      render(
        <NeonKanbanBoard
          columns={[column("research", "Research", 1)]}
          labels={labels}
        />,
      );
      const link = screen.getByRole("link", { name: /Research card 0/ });
      link.addEventListener("click", (event) => {
        event.preventDefault();
        clicked = true;
      });
      await user.click(link);
      expect(clicked).toBe(true);
    } finally {
      Object.defineProperty(window, "sessionStorage", {
        value: original,
        configurable: true,
      });
    }
  });

  /** Scenario: Expanded rails persist across reloads */
  it("expands a rail that localStorage remembers", () => {
    window.localStorage.setItem(
      WORKFLOW_BOARD_EXPANDED_STORAGE_KEY,
      JSON.stringify(["published"]),
    );
    render(
      <NeonKanbanBoard
        columns={[column("published", "Published", 2)]}
        labels={labels}
      />,
    );
    expect(screen.getByTestId("workflow-column-published")).not.toBeNull();
  });

  /** Scenario: An expanded empty column explains itself */
  it("shows the empty-column text in an expanded empty column", async () => {
    const user = userEvent.setup();
    render(
      <NeonKanbanBoard
        columns={[column("brief", "Brief", 0)]}
        labels={labels}
      />,
    );
    await user.click(
      screen.getByRole("button", { name: "Expandir coluna Brief (0)" }),
    );
    expect(screen.getByText("Nenhum projeto")).toBeInTheDocument();
  });

  /** Scenario: Returning from a carousel restores the board scroll */
  it("saves the board scroll before a card navigation", async () => {
    const user = userEvent.setup();
    render(
      <NeonKanbanBoard
        columns={[column("research", "Research", 1)]}
        labels={labels}
      />,
    );
    const link = screen.getByRole("link", { name: /Research card 0/ });
    link.addEventListener("click", (event) => event.preventDefault());
    await user.click(link);
    const saved = JSON.parse(
      window.sessionStorage.getItem(
        `${WORKFLOW_BOARD_SCROLL_STORAGE_PREFIX}:active`,
      ) ?? "{}",
    ) as { left?: unknown; tops?: unknown };
    expect(typeof saved.left).toBe("number");
    expect(typeof saved.tops).toBe("object");
  });

  /** Scenario: Previous and next controls follow the board column sequence */
  it("stores the clicked card column sequence for workspace navigation", async () => {
    const user = userEvent.setup();
    render(
      <NeonKanbanBoard
        columns={[column("final_review", "Final review", 3)]}
        labels={labels}
      />,
    );
    const link = screen.getByRole("link", { name: /Final review card 1/ });
    link.addEventListener("click", (event) => event.preventDefault());
    await user.click(link);
    expect(
      JSON.parse(
        window.sessionStorage.getItem(WORKFLOW_BOARD_SEQUENCE_STORAGE_KEY) ??
          "{}",
      ),
    ).toEqual({
      column: "Final review",
      ids: ["final_review-0", "final_review-1", "final_review-2"],
    });
  });

  /** Scenario: Badges use semantic colors */
  it("renders the card badge with the semantic variant and pulse", () => {
    render(
      <NeonKanbanBoard
        columns={[
          cardsColumn("final_review", "Final review", [
            {
              id: "card-need",
              title: "Needs the owner",
              description: "",
              phase: "final_review",
              phaseStatus: "Precisa de você",
              statusKey: "awaiting_human",
              statusVariant: "magenta",
            },
            {
              id: "card-live",
              title: "Generating",
              description: "",
              phase: "images",
              phaseStatus: "Em andamento",
              statusKey: "in_progress",
              statusVariant: "cyan",
              statusPulse: true,
            },
          ]),
        ]}
        labels={labels}
      />,
    );
    const needBadge = screen.getByText("Precisa de você").closest("span");
    expect(needBadge?.style.color).toBe(badgeColor("magenta"));
    const liveBadge = screen.getByText("Em andamento").closest("span");
    expect(liveBadge?.style.color).toBe(badgeColor("cyan"));
    expect(liveBadge?.querySelector(".animate-pulse")).not.toBeNull();
    expect(needBadge?.querySelector(".animate-pulse")).toBeNull();
  });

  /** Scenario: Badges use semantic colors */
  it("labels each card link with the title and status", () => {
    render(
      <NeonKanbanBoard
        columns={[
          cardsColumn("research", "Research", [
            {
              id: "card-1",
              title: "DeepSeek V4",
              description: "Research benchmarks",
              phase: "research",
              phaseStatus: "Pending",
              statusKey: "pending",
            },
          ]),
        ]}
        labels={labels}
      />,
    );
    expect(screen.getByRole("link")).toHaveAttribute(
      "aria-label",
      "DeepSeek V4, Pending",
    );
  });

  /** Scenario: The published column stops saying ready to publish */
  it("shows the relative updated time instead of a badge in the published column", () => {
    window.localStorage.setItem(
      WORKFLOW_BOARD_EXPANDED_STORAGE_KEY,
      JSON.stringify(["published"]),
    );
    render(
      <NeonKanbanBoard
        columns={[
          cardsColumn("published", "Published", [
            {
              id: "card-pub",
              title: "Published carousel",
              description: "",
              phase: "published",
              phaseStatus: "Pronto para publicar",
              statusKey: "approved_for_publish",
              statusVariant: "teal",
              updatedAt: "2026-10-27T12:00:00Z",
            },
          ]),
        ]}
        labels={labels}
      />,
    );
    expect(screen.getByTestId("workflow-column-published")).not.toBeNull();
    const updated = screen.getByTestId("published-updated");
    expect(updated.textContent).not.toBe("");
    expect(updated.textContent).not.toBe("Pronto para publicar");
  });

  /** Scenario: Column headers count the cards that need the owner */
  it("counts the awaiting-owner cards in the column header", () => {
    render(
      <NeonKanbanBoard
        columns={[
          cardsColumn("final_review", "Final review", [
            {
              id: "card-a",
              title: "A",
              description: "",
              phase: "final_review",
              phaseStatus: "x",
              statusKey: "awaiting_human",
            },
            {
              id: "card-b",
              title: "B",
              description: "",
              phase: "final_review",
              phaseStatus: "x",
              statusKey: "awaiting_human",
            },
            {
              id: "card-c",
              title: "C",
              description: "",
              phase: "final_review",
              phaseStatus: "x",
              statusKey: "approved_for_publish",
            },
          ]),
        ]}
        labels={labels}
      />,
    );
    expect(screen.getByTestId("column-need-you")).toHaveTextContent(
      "2 precisam de você",
    );
  });

  it("omits the need-you count when no card awaits the owner", () => {
    render(<NeonKanbanBoard columns={columns} labels={labels} />);
    expect(screen.queryByTestId("column-need-you")).toBeNull();
  });

  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
  });
});
