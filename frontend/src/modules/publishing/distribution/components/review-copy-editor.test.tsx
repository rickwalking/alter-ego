import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import type { CopyEditor } from "@/modules/publishing/distribution/hooks/types";
import {
  ReviewCaptionEditor,
  ReviewCopyLeaveGuard,
  ReviewLinkedInEditor,
} from "./review-copy-editor";

/** Gherkin: tests/features/final-review-copy-edit-ae0505.feature. */

function editor(overrides: Partial<CopyEditor> = {}): CopyEditor {
  return {
    draft: { caption: "c", linkedinPt: "pt", linkedinEn: "en" },
    status: { kind: "idle" },
    canSave: true,
    isDirty: () => true,
    setText: vi.fn(),
    save: vi.fn(() => Promise.resolve()),
    ...overrides,
  };
}

describe("review copy editors (AE-0505)", () => {
  /** Scenario: The reviewer saves an edited caption in the final review */
  it("refuses to save a caption over the Instagram limit", () => {
    render(
      <ReviewCaptionEditor
        editor={editor({
          draft: { caption: "x".repeat(2201), linkedinPt: "", linkedinEn: "" },
        })}
      />,
    );
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
  });

  /** Scenario: The reviewer saves a LinkedIn post per language */
  it("edits the Portuguese post first and saves both languages' edits", () => {
    const current = editor();
    render(<ReviewLinkedInEditor editor={current} />);
    fireEvent.change(screen.getByLabelText("LinkedIn post (PT)"), {
      target: { value: "novo" },
    });
    expect(current.setText).toHaveBeenCalledWith("linkedinPt", "novo");
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(current.save).toHaveBeenCalledWith(["linkedinPt", "linkedinEn"]);
  });

  /** Scenario: Leaving the review with unsaved edits asks first */
  it("asks before an in-app link drops unsaved edits", () => {
    render(
      <>
        <a href="/dashboard">away</a>
        <ReviewCopyLeaveGuard editor={editor()} />
      </>,
    );
    fireEvent.click(screen.getByText("away"));
    expect(screen.getByText("Leave without saving?")).toBeInTheDocument();
  });

  /** Scenario: Leaving the review with unsaved edits asks first */
  it("lets the link through when nothing is unsaved", () => {
    render(
      <>
        <a href="#here">away</a>
        <ReviewCopyLeaveGuard editor={editor({ isDirty: () => false })} />
      </>,
    );
    fireEvent.click(screen.getByText("away"));
    expect(screen.queryByText("Leave without saving?")).not.toBeInTheDocument();
  });
});
