import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DEFAULT_BOARD_FILTERS } from "@/app/dashboard/workflow/board-filters";
import { WorkflowToolbar } from "./workflow-toolbar";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

const COUNTS = {
  all: 9,
  needsReview: 7,
  inProgress: 0,
  ready: 2,
  failed: 0,
};

describe("WorkflowToolbar", () => {
  /** Scenario: Search narrows the board */
  it("sends the search value to the owner with the current filters", () => {
    const onChange = vi.fn();
    render(
      <WorkflowToolbar
        filters={DEFAULT_BOARD_FILTERS}
        counts={COUNTS}
        onChange={onChange}
      />,
    );
    fireEvent.change(screen.getByRole("searchbox"), {
      target: { value: "claude" },
    });
    expect(onChange).toHaveBeenCalledWith({
      ...DEFAULT_BOARD_FILTERS,
      query: "claude",
    });
  });

  /** Scenario: Search narrows the board */
  it("focuses the search box on slash outside editable fields", () => {
    render(
      <WorkflowToolbar
        filters={DEFAULT_BOARD_FILTERS}
        counts={COUNTS}
        onChange={vi.fn()}
      />,
    );
    const input = screen.getByRole("searchbox");
    expect(input).not.toHaveFocus();
    fireEvent.keyDown(window, { key: "/" });
    expect(input).toHaveFocus();
  });

  /** Scenario: Search narrows the board */
  it("leaves slash alone inside editable fields", () => {
    render(
      <>
        <input aria-label="Notes" />
        <WorkflowToolbar
          filters={DEFAULT_BOARD_FILTERS}
          counts={COUNTS}
          onChange={vi.fn()}
        />
      </>,
    );
    const notes = screen.getByRole("textbox", { name: "Notes" });
    notes.focus();
    fireEvent.keyDown(notes, { key: "/" });
    expect(notes).toHaveFocus();
    expect(screen.getByRole("searchbox")).not.toHaveFocus();
  });

  /** Scenario: Status chips filter by raw status */
  it("presses a status chip with its count and pressed state", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <WorkflowToolbar
        filters={DEFAULT_BOARD_FILTERS}
        counts={COUNTS}
        onChange={onChange}
      />,
    );
    const chip = screen.getByRole("button", {
      name: "filters.needsReview (7)",
    });
    expect(chip).toHaveAttribute("aria-pressed", "false");
    await user.click(chip);
    expect(onChange).toHaveBeenCalledWith({
      ...DEFAULT_BOARD_FILTERS,
      status: "needsReview",
    });
  });

  it("marks the active chip as pressed", () => {
    render(
      <WorkflowToolbar
        filters={{ ...DEFAULT_BOARD_FILTERS, status: "needsReview" }}
        counts={COUNTS}
        onChange={vi.fn()}
      />,
    );
    expect(
      screen.getByRole("button", { name: "filters.needsReview (7)" }),
    ).toHaveAttribute("aria-pressed", "true");
  });

  /** Scenario: Sort follows the toolbar */
  it("switches the sort through the radio group", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <WorkflowToolbar
        filters={DEFAULT_BOARD_FILTERS}
        counts={COUNTS}
        onChange={onChange}
      />,
    );
    const group = screen.getByRole("radiogroup", { name: "sort.label" });
    const updated = screen.getByRole("radio", { name: "sort.updated" });
    const title = screen.getByRole("radio", { name: "sort.title" });
    expect(updated).toHaveAttribute("aria-checked", "true");
    expect(title).toHaveAttribute("aria-checked", "false");
    expect(group).toContainElement(updated);
    await user.click(title);
    expect(onChange).toHaveBeenCalledWith({
      ...DEFAULT_BOARD_FILTERS,
      sort: "title",
    });
  });

  /** Scenario: Sort follows the toolbar */
  it("moves between sort options with the arrow keys", () => {
    const onChange = vi.fn();
    render(
      <WorkflowToolbar
        filters={DEFAULT_BOARD_FILTERS}
        counts={COUNTS}
        onChange={onChange}
      />,
    );
    fireEvent.keyDown(screen.getByRole("radiogroup", { name: "sort.label" }), {
      key: "ArrowRight",
    });
    expect(onChange).toHaveBeenCalledWith({
      ...DEFAULT_BOARD_FILTERS,
      sort: "title",
    });
  });

  /** Scenario: Status chips filter by raw status */
  it("labels the chip group", () => {
    render(
      <WorkflowToolbar
        filters={DEFAULT_BOARD_FILTERS}
        counts={COUNTS}
        onChange={vi.fn()}
      />,
    );
    expect(
      screen.getByRole("group", { name: "filters.group" }),
    ).toBeInTheDocument();
  });
});
