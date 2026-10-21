import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ReviewBar } from "./review-bar";
import type { ReviewBarProps } from "./types";
import { VoiceScore } from "./voice-score";

/** Gherkin: tests/features/blog_editor_ae0424.feature. */

function props(overrides: Partial<ReviewBarProps> = {}): ReviewBarProps {
  return {
    status: "draft",
    scheduledPublishAt: null,
    disabled: false,
    error: null,
    onSubmitReview: vi.fn(),
    onApprove: vi.fn(),
    onReject: vi.fn(),
    onPublish: vi.fn(),
    onPublishNow: vi.fn(),
    onUnpublish: vi.fn(),
    onSchedule: vi.fn(),
    onCancelSchedule: vi.fn(),
    ...overrides,
  };
}

describe("ReviewBar", () => {
  // Scenario: A distinct reviewer can still be named (AE-0441)
  it("submits to a typed reviewer id", () => {
    const p = props();
    render(<ReviewBar {...p} />);
    const submit = screen.getByRole("button", { name: "Submit for review" });
    expect(submit).toBeEnabled();
    fireEvent.change(screen.getByLabelText("Reviewer ID"), {
      target: { value: " rev-1 " },
    });
    fireEvent.click(submit);
    expect(p.onSubmitReview).toHaveBeenCalledWith("rev-1");
  });

  // Scenario: Publishing a draft is blocked by the status guard (the API answers)
  it("lets Publish reach the status guard on a draft", () => {
    const p = props();
    render(<ReviewBar {...p} />);
    fireEvent.click(screen.getByRole("button", { name: "Publish" }));
    expect(p.onPublish).toHaveBeenCalled();
  });

  // Scenario: Publish now auto-approves the owner's draft
  // Scenario: Self-review is allowed for the single author
  it("always offers Publish now and a self submit on a draft", () => {
    const p = props();
    render(<ReviewBar {...p} />);
    expect(screen.getByText(/leave it empty/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Publish now" }));
    expect(p.onPublishNow).toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Submit for review" }));
    expect(p.onSubmitReview).toHaveBeenCalledWith(null);
  });

  // Scenario: Approve / Reject returns the post to draft with a reason
  it("approves or rejects with a reason when under review", () => {
    const p = props({ status: "under_review" });
    render(<ReviewBar {...p} />);
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    expect(p.onApprove).toHaveBeenCalled();
    const reject = screen.getByRole("button", { name: "Reject" });
    expect(reject).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Reason for rejection"), {
      target: { value: "Falta fonte" },
    });
    fireEvent.click(reject);
    expect(p.onReject).toHaveBeenCalledWith("Falta fonte");
  });

  // Scenario: Scheduling publishes at the chosen time
  it("publishes or schedules an approved post", () => {
    const p = props({ status: "approved" });
    render(<ReviewBar {...p} />);
    fireEvent.click(screen.getByRole("button", { name: "Publish" }));
    expect(p.onPublish).toHaveBeenCalled();
    const schedule = screen.getByRole("button", { name: "Schedule" });
    expect(schedule).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Publish at"), {
      target: { value: "2026-10-25T10:00" },
    });
    fireEvent.click(schedule);
    expect(p.onSchedule).toHaveBeenCalledWith(
      new Date("2026-10-25T10:00").toISOString(),
    );
  });

  // Scenario: Cancelling a schedule leaves the post approved
  it("cancels an existing schedule", () => {
    const p = props({
      status: "approved",
      scheduledPublishAt: "2026-10-25T10:00:00Z",
    });
    render(<ReviewBar {...p} />);
    expect(screen.getByText(/Scheduled for/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Cancel schedule" }));
    expect(p.onCancelSchedule).toHaveBeenCalled();
  });

  // Scenario: Unpublish returns the post to draft and 404s publicly
  it("unpublishes a published post and disables everything while busy", () => {
    const p = props({ status: "published" });
    const { rerender } = render(<ReviewBar {...p} />);
    fireEvent.click(screen.getByRole("button", { name: "Unpublish" }));
    expect(p.onUnpublish).toHaveBeenCalled();
    rerender(<ReviewBar {...p} disabled />);
    expect(screen.getByRole("button", { name: "Unpublish" })).toBeDisabled();
    expect(screen.getByText("Published")).toBeInTheDocument();
  });

  // Scenario: A publish blocked by the status guard is explained (AE-0438, F-11)
  it("shows the status-guard error inside the review bar", () => {
    const p = props({ error: { kind: "status_guard", detail: null } });
    render(<ReviewBar {...p} />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("shows a generic failure with the code-specific copy when known", () => {
    const p = props({
      error: { kind: "failed", detail: "blog_document_not_publishable" },
    });
    render(<ReviewBar {...p} />);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "cannot be published yet",
    );
  });
});

describe("VoiceScore", () => {
  // Scenario: The voice score is shown from content.quality
  it("shows the score and its breakdown", () => {
    const onPersonaChange = vi.fn();
    render(
      <VoiceScore
        quality={{
          voice_score: 82,
          voice_breakdown: { tone_match: 80, suggestions: ["x"] },
        }}
        personas={[
          { id: "a", name: "Pedro's Professional Voice" },
          { id: "b", name: "B" },
        ]}
        personaId="a"
        onPersonaChange={onPersonaChange}
      />,
    );
    expect(screen.getByText("82/100")).toBeInTheDocument();
    expect(screen.getByText("tone_match")).toBeInTheDocument();
    expect(screen.queryByText("suggestions")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Voice persona"), {
      target: { value: "b" },
    });
    expect(onPersonaChange).toHaveBeenCalledWith("b");
  });

  it("says not scored and handles no persona", () => {
    render(
      <VoiceScore
        quality={null}
        personas={[]}
        personaId={null}
        onPersonaChange={vi.fn()}
      />,
    );
    expect(screen.getByText("Not scored yet")).toBeInTheDocument();
    expect(screen.getByText("No persona available")).toBeInTheDocument();
  });

  it("marks a score below the bar", () => {
    render(
      <VoiceScore
        quality={{ voice_score: 55.4 }}
        personas={[]}
        personaId={null}
        onPersonaChange={vi.fn()}
      />,
    );
    expect(screen.getByText("55/100")).toBeInTheDocument();
  });
});
