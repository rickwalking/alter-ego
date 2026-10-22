import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@/test/utils";
import { PaletteCard } from "./palette-card";

const BASE = {
  name: "Aurora",
  primary: "#102030",
  accent: "#405060",
  background: "#708090",
  mode: "dark" as const,
};

describe("PaletteCard", () => {
  it("renders a root palette read-only (no edit/archive)", () => {
    render(<PaletteCard {...BASE} name="Plasma Magenta" isRoot />);
    expect(screen.getByText("Plasma Magenta")).toBeInTheDocument();
    expect(screen.getByText("root")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /edit/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /archive/i })).toBeNull();
  });

  it("renders keywords and edit/archive for a custom palette", () => {
    render(
      <PaletteCard {...BASE} keywords={["space", "neon"]} isRoot={false} />,
    );
    expect(screen.getByText("space")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /edit/i })).toBeInTheDocument();
  });

  it("requires a confirm step before archiving", () => {
    const onArchive = vi.fn();
    render(<PaletteCard {...BASE} isRoot={false} onArchive={onArchive} />);
    fireEvent.click(screen.getByRole("button", { name: /^archive$/i }));
    expect(screen.getByText(/archive this palette/i)).toBeInTheDocument();
    expect(onArchive).not.toHaveBeenCalled();
    const buttons = screen.getAllByRole("button", { name: /archive/i });
    fireEvent.click(buttons[buttons.length - 1]!);
    expect(onArchive).toHaveBeenCalledTimes(1);
  });

  it("shows the archive question on its own line above the buttons", () => {
    // Scenario: The archive question sits on its own line above the buttons
    render(<PaletteCard {...BASE} isRoot={false} />);
    fireEvent.click(screen.getByRole("button", { name: /^archive$/i }));
    const group = screen.getByRole("group", { name: "Archive this palette?" });
    const question = within(group).getByText("Archive this palette?");
    const cancel = within(group).getByRole("button", { name: /cancel/i });
    const confirm = within(group).getByRole("button", { name: /^archive$/i });
    expect(question.tagName).toBe("P");
    expect(question.parentElement).toBe(group);
    expect(cancel.parentElement).not.toBe(group);
    expect(cancel.parentElement).toBe(confirm.parentElement);
    expect(cancel.parentElement).toHaveClass("flex-wrap");
    expect(
      question.compareDocumentPosition(cancel) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("returns to the card actions when the archive question is cancelled", () => {
    // Scenario: Cancelling the archive question returns to the card actions
    const onArchive = vi.fn();
    render(<PaletteCard {...BASE} isRoot={false} onArchive={onArchive} />);
    fireEvent.click(screen.getByRole("button", { name: /^archive$/i }));
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(
      screen.queryByRole("group", { name: "Archive this palette?" }),
    ).toBeNull();
    expect(screen.getByRole("button", { name: /edit/i })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /^archive$/i }),
    ).toBeInTheDocument();
    expect(onArchive).not.toHaveBeenCalled();
  });

  it("exposes the swatch with an accessible colour description", () => {
    render(<PaletteCard {...BASE} isRoot={false} />);
    expect(
      screen.getByRole("img", { name: /primary #102030/i }),
    ).toBeInTheDocument();
  });
});
