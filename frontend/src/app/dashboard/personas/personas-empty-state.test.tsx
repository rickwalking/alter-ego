/**
 * The personas empty state in English and Portuguese.
 *
 * Gherkin: tests/features/personas-polish-ae0513.feature
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PersonasEmptyState } from "./personas-empty-state";

describe("PersonasEmptyState", () => {
  it("welcomes a first persona with a touch-sized primary action", async () => {
    // Scenario: An empty persona list shows a welcoming empty state with the primary action
    const user = userEvent.setup();
    const onCreate = vi.fn();
    render(<PersonasEmptyState searchQuery="" onCreate={onCreate} />);
    expect(
      screen.getByRole("heading", { name: "No personas yet" }),
    ).toBeInTheDocument();
    const action = screen.getByRole("button", {
      name: "Create your first persona",
    });
    expect(action).toHaveClass("min-h-11");
    await user.click(action);
    expect(onCreate).toHaveBeenCalledOnce();
  });

  it("says a search found nothing, without a create button", () => {
    // Scenario: A search without matches keeps its own title
    render(<PersonasEmptyState searchQuery="zzz" onCreate={vi.fn()} />);
    expect(
      screen.getByRole("heading", { name: "No personas found" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText('No results for "zzz". Try a different search term.'),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
