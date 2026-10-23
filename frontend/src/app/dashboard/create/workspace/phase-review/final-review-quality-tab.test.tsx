import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import type { EditorialWorkflowState } from "@/modules/publishing";
import { QualityTab } from "./final-review-quality-tab";

/** Gherkin: tests/features/carousel-rubric-ae0504.feature. */

function state(rubricScores: Record<string, unknown>): EditorialWorkflowState {
  return {
    project_id: "p1",
    current_phase: "final_review",
    rubric_scores: rubricScores,
  } as EditorialWorkflowState;
}

const SCORED = {
  rubric_id: "r1",
  rubric_name: "QA",
  overall_score: 74,
  passed: false,
  feedback: "Bom ritmo",
  criteria: [
    {
      id: "clarity",
      name: "Clareza",
      score: 82,
      threshold: 70,
      passed: true,
      feedback: "",
    },
    {
      id: "proof",
      name: "Prova",
      score: 55,
      threshold: 60,
      passed: false,
      feedback: "Falta exemplo",
    },
    { id: "broken", name: "Sem nota" },
  ],
};

describe("QualityTab (AE-0504)", () => {
  /** Scenario: Final review shows each criterion's score against its threshold */
  it("shows the rubric, the overall score and each criterion vs its minimum", () => {
    render(<QualityTab state={state(SCORED)} emptyText="empty" />);

    expect(
      screen.getByText("Rubric QA: overall score 74/100"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Some criteria are below their minimum."),
    ).toBeInTheDocument();
    const rows = screen.getAllByRole("listitem");
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent("Clareza82/100 (minimum 70)");
    expect(rows[0]).not.toHaveTextContent("Below the minimum");
    expect(rows[1]).toHaveTextContent("55/100 (minimum 60)");
    expect(rows[1]).toHaveTextContent("Below the minimum");
    expect(rows[1]).toHaveTextContent("Falta exemplo");
    expect(screen.getByText("Bom ritmo")).toBeInTheDocument();
  });

  /** Scenario: Final review shows each criterion's score against its threshold */
  it("says so when every criterion reached its minimum", () => {
    render(
      <QualityTab
        state={state({
          ...SCORED,
          passed: true,
          criteria: [SCORED.criteria[0]],
          feedback: "",
        })}
        emptyText="empty"
      />,
    );
    expect(
      screen.getByText("Every criterion reached its minimum."),
    ).toBeInTheDocument();
  });

  /** Scenario: Final review without rubric scores */
  it("shows the empty note without scores, and other score maps as rows", () => {
    const { rerender } = render(
      <QualityTab state={state({})} emptyText="empty" />,
    );
    expect(screen.getByText("empty")).toBeInTheDocument();

    rerender(
      <QualityTab
        state={state({ voice_match: "82", detail: { a: 1 } })}
        emptyText="empty"
      />,
    );
    expect(screen.getByText("voice match")).toBeInTheDocument();
    expect(screen.getByText("82")).toBeInTheDocument();
    expect(screen.getByText('{"a":1}')).toBeInTheDocument();
  });

  /** Scenario: Final review without rubric scores */
  it("shows the empty note, never 0/100, when the overall score is missing", () => {
    const withoutOverall: Record<string, unknown> = { ...SCORED };
    delete withoutOverall.overall_score;
    render(<QualityTab state={state(withoutOverall)} emptyText="empty" />);
    expect(screen.queryByText(/overall score/)).not.toBeInTheDocument();
    expect(screen.queryByText(/0\/100/)).not.toBeInTheDocument();
  });
});
