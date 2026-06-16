import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { NeonKanbanBoard } from "@/modules/editorial-operations";

// Feature: NeonKanbanBoard Component
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
});
