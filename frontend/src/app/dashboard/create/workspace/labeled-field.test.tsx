/**
 * AE-0154: shared LabeledField for the create-carousel workspace sections.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { LabeledField } from "./labeled-field";

describe("LabeledField", () => {
  it("renders the label and optional hint", () => {
    render(
      <LabeledField
        label="Carousel Topic"
        hint="max 500 chars"
        value=""
        onChange={() => {}}
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
        onChange={() => {}}
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
        onChange={() => {}}
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
        onChange={() => {}}
        marginBottom="14px"
      />,
    );
    // The field wrapper is the input's parent <div>.
    expect(screen.getByRole("textbox").parentElement).toHaveStyle({
      marginBottom: "14px",
    });

    rerender(<LabeledField label="A" value="" onChange={() => {}} />);
    expect(screen.getByRole("textbox").parentElement?.style.marginBottom).toBe(
      "",
    );
  });

  it("omits the hint span when no hint is given", () => {
    render(<LabeledField label="Topic" value="" onChange={() => {}} />);
    expect(screen.queryByText(/\(.*\)/)).not.toBeInTheDocument();
  });
});
