import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@/test/utils";
import { PaletteCard } from "./palette-card";

// Gherkin: tests/features/palette_crud_api.feature (catalog view: roots are
// read-only; custom palettes are editable + archivable — AE-0271).
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
    // After clicking, a confirm prompt appears; the action only fires on confirm.
    expect(screen.getByText(/archive this palette/i)).toBeInTheDocument();
    expect(onArchive).not.toHaveBeenCalled();
    const buttons = screen.getAllByRole("button", { name: /archive/i });
    fireEvent.click(buttons[buttons.length - 1]);
    expect(onArchive).toHaveBeenCalledTimes(1);
  });

  it("exposes the swatch with an accessible colour description", () => {
    render(<PaletteCard {...BASE} isRoot={false} />);
    expect(
      screen.getByRole("img", { name: /primary #102030/i }),
    ).toBeInTheDocument();
  });
});
