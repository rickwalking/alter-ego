import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { INITIAL_CREATE_FORM_STATE } from "@/app/dashboard/create/types";
import { CreateTopicSection } from "./create-topic-section";

// Scenarios: see tests/features/create-image-guidance.feature

describe("CreateTopicSection image guidance (AE-0298)", () => {
  it("renders the optional multiline image-guidance input capped at 500 chars", () => {
    render(
      <CreateTopicSection
        form={INITIAL_CREATE_FORM_STATE}
        onChange={() => undefined}
      />,
    );
    expect(screen.getByText(/Image Guidance/i)).toBeInTheDocument();
    const field = screen.getByPlaceholderText(/misty harbor/i);
    expect(field.tagName).toBe("TEXTAREA");
    expect(field).toHaveAttribute("maxlength", "500");
  });

  it("patches customVisualDetails on change", () => {
    const onChange = vi.fn();
    render(
      <CreateTopicSection
        form={INITIAL_CREATE_FORM_STATE}
        onChange={onChange}
      />,
    );
    fireEvent.change(screen.getByPlaceholderText(/misty harbor/i), {
      target: { value: "misty harbor" },
    });
    expect(onChange).toHaveBeenCalledWith({
      customVisualDetails: "misty harbor",
    });
  });
});
