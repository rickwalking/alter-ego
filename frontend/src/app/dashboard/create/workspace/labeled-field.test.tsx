/**
 * AE-0154: shared LabeledField for the create-carousel workspace sections.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { LabeledField } from "./labeled-field";

/** True when the text holds an opening parenthesis followed later by a closing one. */
function hasParenthesizedText(content: string): boolean {
  const open = content.indexOf("(");
  return open >= 0 && content.includes(")", open + 1);
}

describe("LabeledField", () => {
  it("renders the label and optional hint", () => {
    render(
      <LabeledField
        label="Carousel Topic"
        hint="max 500 chars"
        value=""
        onChange={() => undefined}
      />,
    );
    expect(screen.getByText("Carousel Topic")).toBeInTheDocument();
    expect(screen.getByText("(max 500 chars)")).toBeInTheDocument();
  });

  it("renders a single-line input by default and reports edits", async () => {
    const onChange = vi.fn();
    render(<LabeledField label="Topic" value="" onChange={onChange} />);
    const input = screen.getByRole("textbox");
    expect(input.tagName).toBe("INPUT");
    await userEvent.type(input, "x");
    expect(onChange).toHaveBeenCalledWith("x");
  });

  it("renders a textarea when multiline", () => {
    render(
      <LabeledField
        label="Brief"
        value="hello"
        onChange={() => undefined}
        multiline
      />,
    );
    const field = screen.getByRole("textbox");
    expect(field.tagName).toBe("TEXTAREA");
    expect(field).toHaveValue("hello");
  });

  it("forwards maxLength to the input element", () => {
    render(
      <LabeledField
        label="Topic"
        value=""
        onChange={() => undefined}
        maxLength={500}
      />,
    );
    expect(screen.getByRole("textbox")).toHaveAttribute("maxLength", "500");
  });

  it("applies marginBottom only when provided", () => {
    const { rerender } = render(
      <LabeledField
        label="A"
        value=""
        onChange={() => undefined}
        marginBottom="14px"
      />,
    );
    // The field wrapper is the input's parent <div>.
    expect(screen.getByRole("textbox").parentElement).toHaveStyle({
      marginBottom: "14px",
    });

    rerender(<LabeledField label="A" value="" onChange={() => undefined} />);
    expect(screen.getByRole("textbox").parentElement?.style.marginBottom).toBe(
      "",
    );
  });

  it("omits the hint span when no hint is given", () => {
    render(<LabeledField label="Topic" value="" onChange={() => undefined} />);
    expect(screen.queryByText(hasParenthesizedText)).not.toBeInTheDocument();
  });
});

// Feature: Create-flow UI fixes (AE-0415)
describe("LabeledField accessibility and limits (AE-0415)", () => {
  // Scenario: Create form labels are tied to their inputs
  it("ties the label to the input and the textarea", () => {
    render(
      <>
        <LabeledField label="Topic" value="" onChange={() => undefined} />
        <LabeledField
          label="Brief"
          value=""
          onChange={() => undefined}
          multiline
        />
      </>,
    );
    expect(screen.getByLabelText("Topic").tagName).toBe("INPUT");
    expect(screen.getByLabelText("Brief").tagName).toBe("TEXTAREA");
  });

  // Scenario: Fields with a limit show a live counter
  it("shows a count/max counter described by the field", () => {
    render(
      <LabeledField
        label="Topic"
        value="twelve chars"
        onChange={() => undefined}
        maxLength={500}
      />,
    );
    const counter = screen.getByText("12/500");
    expect(screen.getByLabelText("Topic")).toHaveAttribute(
      "aria-describedby",
      counter.id,
    );
  });

  it("shows no counter without a limit", () => {
    render(
      <LabeledField label="Topic" value="abc" onChange={() => undefined} />,
    );
    expect(screen.queryByText(/\/\d+$/)).not.toBeInTheDocument();
    expect(screen.getByLabelText("Topic")).not.toHaveAttribute(
      "aria-describedby",
    );
  });
});
