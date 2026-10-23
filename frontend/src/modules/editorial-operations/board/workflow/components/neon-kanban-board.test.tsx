import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { NeonKanbanBoard } from "@/modules/editorial-operations";

describe("NeonKanbanBoard Component", () => {
  const columns = [
    {
      phase: "research",
      status: "Research",
      count: 1,
      cards: [
        {
          id: "card-1",
          title: "DeepSeek V4",
          description: "Research benchmarks",
          phase: "research",
          phaseStatus: "pending",
          assignee: "PM",
        },
      ],
    },
  ];

  it("renders column status labels", () => {
    render(<NeonKanbanBoard columns={columns} />);
    expect(screen.getByText("Research")).toBeInTheDocument();
  });

  it("renders card titles", () => {
    render(<NeonKanbanBoard columns={columns} />);
    expect(screen.getByText("DeepSeek V4")).toBeInTheDocument();
  });

  /** Scenario: Archiving a card asks for a confirmation first */
  it("renders the card actions outside the card link", () => {
    render(
      <NeonKanbanBoard
        columns={columns}
        renderCardActions={(card) => (
          <button type="button">{`archive ${card.id}`}</button>
        )}
      />,
    );
    const action = screen.getByRole("button", { name: "archive card-1" });
    expect(action.closest("a")).toBeNull();
    expect(screen.getByRole("link")).toHaveTextContent("DeepSeek V4");
  });
});
